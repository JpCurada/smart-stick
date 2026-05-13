"""Tracks the current usage session (start time, distance, counters)."""

from __future__ import annotations

import threading
import uuid

from storage import SessionRecord, SessionRepository
from utils.converters import now_utc
from utils.logger import get_logger


class SessionService:
    """Single live session that aggregates counters until ended."""

    def __init__(self, repository: SessionRepository) -> None:
        self._repo = repository
        self._session_id: str | None = None
        self._start_time = None
        self._detection_count = 0
        self._alert_count = 0
        self._distance_km = 0.0
        self._lock = threading.Lock()
        self._log = get_logger("services.session")

    def start(self) -> str:
        with self._lock:
            self._session_id = f"session_{uuid.uuid4().hex[:12]}"
            self._start_time = now_utc()
            self._detection_count = 0
            self._alert_count = 0
            self._distance_km = 0.0
            self._persist(end_time=None)
            return self._session_id

    def end(self) -> dict | None:
        with self._lock:
            if self._session_id is None or self._start_time is None:
                return None
            end_time = now_utc()
            duration = int((end_time - self._start_time).total_seconds() / 60)
            self._persist(end_time=end_time, duration_minutes=duration)
            summary = self.snapshot()
            self._session_id = None
            self._start_time = None
            return summary

    def increment_detections(self, count: int = 1) -> None:
        with self._lock:
            self._detection_count += count
            self._persist(end_time=None)

    def increment_alerts(self, count: int = 1) -> None:
        with self._lock:
            self._alert_count += count
            self._persist(end_time=None)

    def add_distance_km(self, km: float) -> None:
        with self._lock:
            self._distance_km += km
            self._persist(end_time=None)

    def snapshot(self) -> dict:
        with self._lock:
            duration_min: int | None = None
            if self._start_time is not None:
                duration_min = int((now_utc() - self._start_time).total_seconds() / 60)
            return {
                "session_id": self._session_id,
                "start_time": self._start_time.isoformat() if self._start_time else None,
                "duration_minutes": duration_min,
                "distance_km": round(self._distance_km, 3),
                "detection_count": self._detection_count,
                "alert_count": self._alert_count,
            }

    def _persist(self, end_time, duration_minutes: int | None = None) -> None:
        if self._session_id is None or self._start_time is None:
            return
        try:
            self._repo.save(
                SessionRecord(
                    session_id=self._session_id,
                    start_time=self._start_time,
                    end_time=end_time,
                    duration_minutes=duration_minutes,
                    distance_km=self._distance_km,
                    detection_count=self._detection_count,
                    alert_count=self._alert_count,
                )
            )
        except Exception as exc:
            self._log.debug("session save failed: %s", exc)
