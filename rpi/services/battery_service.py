"""Polls the battery sensor, persists status, and triggers warnings."""

from __future__ import annotations

import threading
import time
from collections.abc import Callable

from core.config import Config
from core.constants import (
    BATTERY_WARNING_MESSAGES,
    BATTERY_WARNING_THRESHOLDS,
    BUZZER_TONES,
)
from sensors.battery import BatterySensor
from storage import BatteryRecord, BatteryRepository
from storage.repositories import encode_json
from utils.converters import unix_timestamp
from utils.logger import get_logger


class BatteryService:
    """Battery polling + warning dispatcher.

    Output is triggered by injecting a callable so this service has no
    dependency on the output module directly (keeps the layering clean).
    """

    def __init__(
        self,
        sensor: BatterySensor,
        repository: BatteryRepository,
        on_warning: Callable[..., None] | None = None,
        on_critical_buzz: Callable[..., None] | None = None,
        interval_s: int | None = None,
    ) -> None:
        self._sensor = sensor
        self._repo = repository
        self._on_warning = on_warning  # callable(message, tone)
        self._on_critical_buzz = on_critical_buzz  # callable(tone)
        self._interval_s = (
            interval_s if interval_s is not None else Config.BATTERY_UPDATE_INTERVAL_S
        )
        self._stop_flag = threading.Event()
        self._thread: threading.Thread | None = None
        self._warned_levels: set[int] = set()
        self._last_critical_announce: float = 0.0
        self._latest: dict | None = None
        self._lock = threading.Lock()
        self._log = get_logger("services.battery")

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._sensor.initialize()
        self._stop_flag.clear()
        self._thread = threading.Thread(target=self._run, name="battery", daemon=True)
        self._thread.start()

    def stop(self, timeout_s: float = 2.0) -> None:
        self._stop_flag.set()
        if self._thread is not None:
            self._thread.join(timeout=timeout_s)
            self._thread = None

    def latest(self) -> dict | None:
        with self._lock:
            return dict(self._latest) if self._latest else None

    def _run(self) -> None:
        while not self._stop_flag.is_set():
            try:
                self._tick()
            except Exception as exc:
                self._log.debug("battery tick failed: %s", exc)
            time.sleep(self._interval_s)

    def _tick(self) -> None:
        reading = self._sensor.read()
        if not reading.healthy:
            return
        payload = dict(reading.data)
        payload["estimated_runtime_minutes"] = self._estimate_runtime(payload)
        with self._lock:
            self._latest = payload
        self._persist(payload, reading.timestamp)
        self._evaluate_warnings(payload)

    def _persist(self, payload: dict, ts) -> None:
        record = BatteryRecord(
            timestamp=ts,
            unix_ts=unix_timestamp(ts),
            voltage=payload["voltage_v"],
            current=payload.get("current_ma"),
            percentage=payload["percentage"],
            temperature=payload.get("temperature_c"),
            health_status=payload["health"],
            status_json=encode_json(payload),
        )
        try:
            self._repo.save(record)
        except Exception as exc:
            self._log.debug("battery save failed: %s", exc)

    def _evaluate_warnings(self, payload: dict) -> None:
        percentage = payload["percentage"]
        for threshold in BATTERY_WARNING_THRESHOLDS:
            if percentage > threshold:
                continue
            if not self._should_announce(threshold):
                continue
            message = BATTERY_WARNING_MESSAGES[threshold]
            tone = BUZZER_TONES["battery_warning"]
            if self._on_warning is not None:
                self._on_warning(message, tone)
            self._warned_levels.add(threshold)
            self._last_critical_announce = time.monotonic()
            break

    def _should_announce(self, threshold: int) -> bool:
        if threshold == 10:
            if 10 not in self._warned_levels:
                return True
            return (time.monotonic() - self._last_critical_announce) > 60.0
        if threshold == 25 and Config.BATTERY_WARN_25 and 25 not in self._warned_levels:
            return True
        if threshold == 50 and Config.BATTERY_WARN_50 and 50 not in self._warned_levels:
            return True
        return False

    @staticmethod
    def _estimate_runtime(payload: dict) -> int:
        """Crude estimate: 10 Ah / current_ma * percentage / 100."""
        current_ma = payload.get("current_ma") or 2500
        percentage = payload["percentage"]
        capacity_mah = 10_000
        remaining_mah = capacity_mah * (percentage / 100.0)
        if current_ma <= 0:
            return 0
        hours = remaining_mah / current_ma
        return int(hours * 60.0)
