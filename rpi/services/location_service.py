"""Reads GPS and persists locations on a fixed cadence."""

from __future__ import annotations

import threading
import time
import uuid

from core.config import Config
from sensors import GpsSensor
from storage import LocationRecord, LocationRepository
from storage.repositories import encode_json
from utils.converters import unix_timestamp
from utils.geometry import haversine_distance_m
from utils.logger import get_logger


class LocationService:
    """Polls the GPS sensor and records fixes to the database."""

    def __init__(
        self,
        gps: GpsSensor,
        repository: LocationRepository,
        interval_s: int | None = None,
    ) -> None:
        self._gps = gps
        self._repo = repository
        self._interval_s = interval_s if interval_s is not None else Config.GPS_UPDATE_INTERVAL_S
        self._stop_flag = threading.Event()
        self._thread: threading.Thread | None = None
        self._latest: dict | None = None
        self._last_recorded: dict | None = None
        self._distance_today_km = 0.0
        self._lock = threading.Lock()
        self._log = get_logger("services.location")

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._gps.initialize()
        self._stop_flag.clear()
        self._thread = threading.Thread(target=self._run, name="location", daemon=True)
        self._thread.start()

    def stop(self, timeout_s: float = 2.0) -> None:
        self._stop_flag.set()
        if self._thread is not None:
            self._thread.join(timeout=timeout_s)
            self._thread = None

    def latest(self) -> dict | None:
        with self._lock:
            return dict(self._latest) if self._latest else None

    def distance_today_km(self) -> float:
        return round(self._distance_today_km, 3)

    def _run(self) -> None:
        while not self._stop_flag.is_set():
            try:
                self._poll_once()
            except Exception as exc:
                self._log.debug("location poll error: %s", exc)
            time.sleep(self._interval_s)

    def _poll_once(self) -> None:
        reading = self._gps.read()
        if not reading.healthy:
            return
        payload = dict(reading.data)
        payload["timestamp"] = reading.timestamp.isoformat()

        with self._lock:
            self._latest = payload
        self._accumulate_distance(payload)
        self._persist(payload, reading.timestamp)

    def _persist(self, payload: dict, ts) -> None:
        location_id = f"loc_{uuid.uuid4().hex[:12]}"
        record = LocationRecord(
            location_id=location_id,
            timestamp=ts,
            unix_ts=unix_timestamp(ts),
            latitude=payload["latitude"],
            longitude=payload["longitude"],
            altitude=payload.get("altitude"),
            accuracy=payload.get("accuracy_m"),
            speed=payload.get("speed"),
            location_json=encode_json(payload),
        )
        try:
            self._repo.save(record)
        except Exception as exc:
            self._log.debug("location save failed: %s", exc)

    def _accumulate_distance(self, payload: dict) -> None:
        if self._last_recorded is not None:
            distance_m = haversine_distance_m(
                self._last_recorded["latitude"],
                self._last_recorded["longitude"],
                payload["latitude"],
                payload["longitude"],
            )
            if distance_m < 200.0:  # ignore jumps from bad fixes
                self._distance_today_km += distance_m / 1000.0
        self._last_recorded = payload
