"""Periodic electrical / system metrics logger.

Writes both to the SQLite electrical_log table and to a CSV file matching
the schema documented in docs/data-schema.md.
"""

from __future__ import annotations

import csv
import threading
import time
from collections.abc import Callable
from pathlib import Path

from core.config import Config
from storage import ElectricalRecord, ElectricalRepository
from utils.converters import iso_timestamp, now_utc
from utils.logger import get_logger

_CSV_HEADERS = (
    "timestamp",
    "battery_voltage_v",
    "battery_current_ma",
    "battery_percentage",
    "rpi_temp_c",
    "esp32_temp_c",
    "wifi_signal_strength_db",
    "detection_fps",
    "inference_time_ms",
    "memory_usage_mb",
    "uptime_seconds",
)


def _rpi_cpu_temp_c() -> float | None:
    path = "/sys/class/thermal/thermal_zone0/temp"
    try:
        with open(path, encoding="ascii") as fh:
            return int(fh.read().strip()) / 1000.0
    except OSError:
        return None


def _memory_usage_mb() -> int | None:
    try:
        import psutil  # type: ignore[import-not-found]

        return int(psutil.virtual_memory().used / (1024 * 1024))
    except Exception:
        return None


def _memory_usage_percent() -> float | None:
    try:
        import psutil  # type: ignore[import-not-found]

        return float(psutil.virtual_memory().percent)
    except Exception:
        return None


class ElectricalLoggerService:
    """Logs power/system metrics on a fixed interval."""

    def __init__(
        self,
        repository: ElectricalRepository,
        battery_snapshot: Callable[[], dict | None],
        fps_callback: Callable[[], float],
        inference_ms_callback: Callable[[], int],
        csv_path: Path | None = None,
        interval_s: int | None = None,
    ) -> None:
        self._repo = repository
        self._battery_snapshot = battery_snapshot
        self._fps = fps_callback
        self._inference_ms = inference_ms_callback
        self._csv_path = csv_path or Config.CSV_LOG_PATH
        self._interval_s = (
            interval_s if interval_s is not None else Config.ELECTRICAL_LOG_INTERVAL_S
        )
        self._stop_flag = threading.Event()
        self._thread: threading.Thread | None = None
        self._start_time = time.monotonic()
        self._log = get_logger("services.electrical")

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._csv_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_csv_header()
        self._stop_flag.clear()
        self._thread = threading.Thread(target=self._run, name="electrical", daemon=True)
        self._thread.start()

    def stop(self, timeout_s: float = 2.0) -> None:
        self._stop_flag.set()
        if self._thread is not None:
            self._thread.join(timeout=timeout_s)
            self._thread = None

    def _run(self) -> None:
        while not self._stop_flag.is_set():
            try:
                self._sample()
            except Exception as exc:
                self._log.debug("electrical sample failed: %s", exc)
            time.sleep(self._interval_s)

    def _sample(self) -> None:
        battery = self._battery_snapshot() or {}
        ts = now_utc()
        record = ElectricalRecord(
            timestamp=ts,
            battery_voltage_v=float(battery.get("voltage_v", 0.0)),
            battery_current_ma=battery.get("current_ma"),
            battery_percentage=battery.get("percentage"),
            rpi_temp_c=_rpi_cpu_temp_c(),
            esp32_temp_c=None,
            wifi_signal_strength_db=None,
            detection_fps=round(self._fps(), 2),
            inference_time_ms=self._inference_ms(),
            memory_usage_mb=_memory_usage_mb(),
            memory_usage_percent=_memory_usage_percent(),
            uptime_seconds=int(time.monotonic() - self._start_time),
        )
        try:
            self._repo.save(record)
        except Exception as exc:
            self._log.debug("electrical save failed: %s", exc)
        self._append_csv(record)

    def _ensure_csv_header(self) -> None:
        if self._csv_path.exists() and self._csv_path.stat().st_size > 0:
            return
        with open(self._csv_path, "w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow(_CSV_HEADERS)

    def _append_csv(self, record: ElectricalRecord) -> None:
        try:
            with open(self._csv_path, "a", newline="", encoding="utf-8") as fh:
                writer = csv.writer(fh)
                writer.writerow(
                    [
                        iso_timestamp(record.timestamp),
                        record.battery_voltage_v,
                        record.battery_current_ma,
                        record.battery_percentage,
                        record.rpi_temp_c,
                        record.esp32_temp_c,
                        record.wifi_signal_strength_db,
                        record.detection_fps,
                        record.inference_time_ms,
                        record.memory_usage_mb,
                        record.uptime_seconds,
                    ]
                )
        except OSError as exc:
            self._log.debug("CSV append failed: %s", exc)
