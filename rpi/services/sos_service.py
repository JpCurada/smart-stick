"""Watch the ESP32 telemetry packet for the SOS flag and surface the event.

The ESP32 firmware sets ``sos_active = 1`` in its SPI packet when the cane
user holds the physical SOS button. This service polls the telemetry
sensor on a background thread, detects the **rising edge** of that flag
(false -> true), and records the event so the mobile app can pick it up
on its next ``GET /api/status`` poll.

Notification strategy
---------------------
This project intentionally has no OS push notifications. The mobile app
is foreground-only: when the guardian opens it, it polls ``/api/status``
and renders an in-app red banner whenever ``sos`` is fresh and not yet
acknowledged. This keeps the whole stack on the local network with no
cloud dependency.

The latest event is exposed via :meth:`latest_event` and consumed by the
``/api/status`` route.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

from sensors import StickTelemetrySensor
from utils.logger import get_logger

# Minimum gap between two consecutive SOS rising-edge events. Prevents a
# bouncy button or quick double-press from publishing two events back to
# back; the second is dropped silently.
_DEFAULT_COOLDOWN_S = 10.0

# How often the watcher polls the telemetry sensor.
_DEFAULT_POLL_INTERVAL_S = 0.5


LocationGetter = Callable[[], dict[str, Any] | None]


class SosService:
    """Background watcher that records SOS events for the in-app banner."""

    def __init__(
        self,
        telemetry: StickTelemetrySensor,
        location_getter: LocationGetter,
        cooldown_s: float = _DEFAULT_COOLDOWN_S,
        poll_interval_s: float = _DEFAULT_POLL_INTERVAL_S,
    ) -> None:
        self._telemetry = telemetry
        self._location_getter = location_getter
        self._cooldown_s = cooldown_s
        self._poll_interval_s = poll_interval_s
        self._stop_flag = threading.Event()
        self._thread: threading.Thread | None = None
        self._last_sos_state = False
        self._last_healthy_read_at: float = 0.0
        self._last_fired_at = 0.0
        self._edge_detected_at: float | None = None
        self._latest_event: dict[str, Any] | None = None
        self._lock = threading.Lock()
        self._log = get_logger("services.sos")

    def latest_event(self) -> dict[str, Any] | None:
        """Most recent SOS event payload (or ``None``). Used by ``/api/status``."""
        with self._lock:
            return dict(self._latest_event) if self._latest_event else None

    def is_active(self) -> bool:
        """True while the ESP32 reports the SOS button as held down.

        Used by OutputService to suppress detection haptics + buzzer so
        the SOS pattern reaches the user unambiguously. Returns False if
        the last healthy telemetry read is stale (>3x the poll interval) —
        prevents detection feedback from being permanently suppressed if
        the SPI link drops while the flag was last seen as held.
        """
        if not self._last_sos_state:
            return False
        stale_after = self._poll_interval_s * 3
        if time.monotonic() - self._last_healthy_read_at > stale_after:
            return False
        return True

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_flag.clear()
        self._thread = threading.Thread(target=self._run, name="sos-watcher", daemon=True)
        self._thread.start()
        self._log.info("sos watcher started")

    def stop(self, timeout_s: float = 2.0) -> None:
        self._stop_flag.set()
        if self._thread is not None:
            self._thread.join(timeout=timeout_s)
            self._thread = None

    def fire_test(self) -> dict[str, Any]:
        """Publish a synthetic SOS event without the physical button. For QA."""
        self._edge_detected_at = time.monotonic()
        return self._fire(reason="test")

    def _run(self) -> None:
        while not self._stop_flag.is_set():
            try:
                reading = self._telemetry.read()
                if reading.healthy:
                    self._last_healthy_read_at = time.monotonic()
                    sos_now = bool(reading.data.get("sos_active"))
                    if sos_now and not self._last_sos_state:
                        # Capture the moment we *saw* the rising edge so the
                        # latency measured in _fire() includes any time spent
                        # inside the cooldown / publish path.
                        self._edge_detected_at = time.monotonic()
                        self._fire(reason="button")
                    self._last_sos_state = sos_now
            except Exception as exc:
                self._log.debug("sos watcher poll error: %s", exc)
            time.sleep(self._poll_interval_s)

    def _fire(self, reason: str) -> dict[str, Any]:
        now = time.monotonic()
        if now - self._last_fired_at < self._cooldown_s:
            self._log.debug("sos fire suppressed (cooldown)")
            return {"published": False, "suppressed": True}
        self._last_fired_at = now

        ts = datetime.now(timezone.utc)
        location = self._location_getter() or {}
        lat = location.get("latitude")
        lng = location.get("longitude")

        if lat is not None and lng is not None:
            maps_url = f"https://maps.google.com/?q={lat:.6f},{lng:.6f}"
        else:
            maps_url = None

        event = {
            "type": "sos",
            "trigger": reason,
            "timestamp": ts.isoformat(),
            "latitude": lat,
            "longitude": lng,
            "maps_url": maps_url,
        }

        self._log.warning("SOS event published (reason=%s)", reason)
        with self._lock:
            self._latest_event = dict(event)

        self._edge_detected_at = None

        return {"published": True, "event": event}
