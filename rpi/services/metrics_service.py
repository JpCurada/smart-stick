"""Lightweight metrics + structured logging for demoable latencies.

The point of this service is **not** to be a Prometheus replacement — it
is to make real measurements visible in the Pi log so they can be shown
during a demo, and to expose the same numbers through ``GET /api/metrics``
for the mobile app.

Recorded metrics
----------------
1. ``obstacle_detection_latency_ms`` — ESP32 flags ``drop``/``overhead``
   in the SPI telemetry. We record the gap between the SPI frame
   arriving on the RPi and the alert being dispatched downstream.
2. ``obstacle_recognition_latency_ms`` — YOLO inference time on the RPi
   for one frame (already tracked by ``DetectionLoop``).
3. ``sos_response_latency_ms`` — time from the SOS rising edge in the
   SPI packet to the event being published to ``/api/status``.
4. ``find_my_stick_latency_ms`` — time from ``POST /api/find`` to the
   SPI command landing on the ESP32.

LSTM sequence-data heartbeat
----------------------------
The "LSTM" (codename) trajectory analyzer described in
``docs/trajectory-design.md`` is not implemented yet. Until it is, this
service emits a once-per-minute heartbeat showing how much of the input
data needed for that analyzer the system has accumulated. That gives
us a real, honest "LSTM sequence data" line in the Pi log without
pretending the model itself exists.

Each call emits ONE structured log line at INFO level so it's
grep-friendly and visible during a live demo without needing any
external tooling.

What this service is NOT
------------------------
* Not a metric for power consumption — the cane has no power sensor.
* Not a metric for "Find My Stick acknowledgement" — the firmware does
  not echo command receipts back over SPI today, so the best we can
  measure is "command sent" not "command obeyed".

Both omissions are deliberate. We chose earlier not to log values we
cannot honestly measure.
"""

from __future__ import annotations

import threading
import time
from collections import deque
from collections.abc import Callable
from typing import Any

from utils.logger import get_logger

# Rolling window of the most recent N samples kept in memory per metric.
# Bigger = smoother averages; smaller = faster response on the demo card.
_HISTORY_SIZE = 50

# How often the LSTM sequence-data heartbeat fires.
_HEARTBEAT_INTERVAL_S = 60.0


# Callback the heartbeat asks for current trajectory-input counts.
TrajectorySnapshotGetter = Callable[[], dict[str, Any]]


class MetricsService:
    """Records timing events, logs them, keeps rolling stats per metric."""

    def __init__(self, trajectory_snapshot: TrajectorySnapshotGetter | None = None) -> None:
        self._log = get_logger("services.metrics")
        self._lock = threading.Lock()
        # Per-metric: rolling history of (timestamp_s, value_ms) tuples.
        self._history: dict[str, deque[tuple[float, float]]] = {}
        self._trajectory_snapshot = trajectory_snapshot
        self._stop_flag = threading.Event()
        self._thread: threading.Thread | None = None

    # ── lifecycle ───────────────────────────────────────────────────────

    def set_trajectory_snapshot(self, getter: TrajectorySnapshotGetter) -> None:
        """Late-bind the snapshot getter. Called after location_service exists."""
        self._trajectory_snapshot = getter

    def start(self) -> None:
        """Start the LSTM sequence-data heartbeat thread."""
        if self._thread is not None and self._thread.is_alive():
            return
        if self._trajectory_snapshot is None:
            self._log.info("metrics service started (no trajectory heartbeat)")
            return
        self._stop_flag.clear()
        self._thread = threading.Thread(
            target=self._heartbeat_run, name="metrics-heartbeat", daemon=True
        )
        self._thread.start()
        self._log.info("metrics service started")

    def stop(self, timeout_s: float = 2.0) -> None:
        self._stop_flag.set()
        if self._thread is not None:
            self._thread.join(timeout=timeout_s)
            self._thread = None

    def _heartbeat_run(self) -> None:
        while not self._stop_flag.is_set():
            try:
                snapshot = self._trajectory_snapshot() if self._trajectory_snapshot else {}
                extras = " ".join(f"{k}={v}" for k, v in snapshot.items())
                self._log.info("metric=lstm_sequence_data %s", extras)
            except Exception as exc:
                self._log.debug("heartbeat snapshot failed: %s", exc)
            self._stop_flag.wait(_HEARTBEAT_INTERVAL_S)

    # ── recording API ───────────────────────────────────────────────────

    def record_obstacle_detection(self, latency_ms: float, source: str) -> None:
        """ESP32 drop/overhead flag → RPi dispatched the alert."""
        self._record(
            "obstacle_detection_latency_ms",
            latency_ms,
            source=source,
        )

    def record_obstacle_recognition(
        self, inference_ms: float, object_class: str, distance_m: float
    ) -> None:
        """One YOLO inference cycle on the RPi."""
        self._record(
            "obstacle_recognition_latency_ms",
            inference_ms,
            object_class=object_class,
            distance_m=round(distance_m, 2),
        )

    def record_sos_response(self, latency_ms: float, trigger: str) -> None:
        """SOS rising edge in SPI → event published for /api/status."""
        self._record(
            "sos_response_latency_ms",
            latency_ms,
            trigger=trigger,
        )

    def record_find_my_stick(self, latency_ms: float, command: str) -> None:
        """POST /api/find received → SPI command landed on the bus."""
        self._record(
            "find_my_stick_latency_ms",
            latency_ms,
            command=command,
        )

    def _record(self, metric: str, value_ms: float, **fields: Any) -> None:
        now_s = time.time()
        with self._lock:
            history = self._history.setdefault(metric, deque(maxlen=_HISTORY_SIZE))
            history.append((now_s, value_ms))
        extras = " ".join(f"{k}={v}" for k, v in fields.items())
        self._log.info(
            "metric=%s value_ms=%.1f %s",
            metric,
            value_ms,
            extras,
        )

    # ── snapshot API (read-only) ────────────────────────────────────────

    def snapshot(self) -> dict[str, Any]:
        """Return a per-metric summary: last, mean over window, count."""
        with self._lock:
            return {metric: self._summarize(samples) for metric, samples in self._history.items()}

    @staticmethod
    def _summarize(samples: deque[tuple[float, float]]) -> dict[str, Any]:
        if not samples:
            return {"count": 0, "last_ms": None, "mean_ms": None}
        values = [v for _, v in samples]
        return {
            "count": len(values),
            "last_ms": round(values[-1], 1),
            "mean_ms": round(sum(values) / len(values), 1),
        }
