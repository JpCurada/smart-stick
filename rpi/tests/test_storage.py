"""Tests for the storage layer (SQLite repositories)."""

from __future__ import annotations

from datetime import timedelta

from storage import (
    BatteryRecord,
    BatteryRepository,
    DetectionRecord,
    DetectionRepository,
    LocationRecord,
    LocationRepository,
)
from storage.migrations import apply_retention
from storage.repositories import encode_json
from utils.converters import now_utc, unix_timestamp


def _detection(frame_id: str = "f1", alert: bool = False) -> DetectionRecord:
    ts = now_utc()
    return DetectionRecord(
        frame_id=frame_id,
        timestamp=ts,
        unix_ts=unix_timestamp(ts),
        detection_json=encode_json({"detections": []}),
        alert_triggered=alert,
        object_count=1,
    )


class TestDetectionRepository:
    def test_save_and_latest(self, database) -> None:
        repo = DetectionRepository(database)
        repo.save(_detection("frame_a"))
        latest = repo.latest()
        assert latest is not None
        assert latest["frame_id"] == "frame_a"

    def test_latest_with_alert_filters_correctly(self, database) -> None:
        repo = DetectionRepository(database)
        repo.save(_detection("frame_no_alert", alert=False))
        repo.save(_detection("frame_alert", alert=True))
        with_alert = repo.latest_with_alert()
        assert with_alert is not None
        assert with_alert["frame_id"] == "frame_alert"

    def test_since_returns_recent_only(self, database) -> None:
        repo = DetectionRepository(database)
        repo.save(_detection("frame_a"))
        since = unix_timestamp() - 60
        rows = repo.since(since)
        assert any(r["frame_id"] == "frame_a" for r in rows)


class TestLocationRepository:
    def test_save_and_latest(self, database) -> None:
        repo = LocationRepository(database)
        ts = now_utc()
        record = LocationRecord(
            location_id="loc_1",
            timestamp=ts,
            unix_ts=unix_timestamp(ts),
            latitude=14.6,
            longitude=120.98,
            location_json="{}",
        )
        repo.save(record)
        latest = repo.latest()
        assert latest is not None
        assert latest["latitude"] == 14.6


class TestBatteryRepository:
    def test_save_and_latest(self, database) -> None:
        repo = BatteryRepository(database)
        ts = now_utc()
        repo.save(
            BatteryRecord(
                timestamp=ts,
                unix_ts=unix_timestamp(ts),
                voltage=4.0,
                current=2000,
                percentage=80,
                temperature=35.0,
                health_status="good",
                status_json="{}",
            )
        )
        latest = repo.latest()
        assert latest["percentage"] == 80


class TestRetention:
    def test_retention_drops_old_rows(self, database) -> None:
        repo = DetectionRepository(database)
        old_ts = now_utc() - timedelta(days=30)
        old = DetectionRecord(
            frame_id="frame_old",
            timestamp=old_ts,
            unix_ts=unix_timestamp(old_ts),
            detection_json="{}",
            alert_triggered=False,
            object_count=0,
        )
        repo.save(old)
        repo.save(_detection("frame_new"))

        before = len(repo.since(0))
        apply_retention(database)
        after = len(repo.since(0))

        assert before == 2
        assert after == 1
        assert repo.latest()["frame_id"] == "frame_new"
