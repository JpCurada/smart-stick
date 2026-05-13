"""Data access objects — high-level save/query operations.

Every repository depends on a shared `Database` instance. SQL lives here
(and only here) for each domain table.
"""

from __future__ import annotations

import json
from typing import Any

from storage.database import Database
from storage.models import (
    AlertRecord,
    BatteryRecord,
    CommandRecord,
    DetectionRecord,
    ElectricalRecord,
    LocationRecord,
    MessageRecord,
    SessionRecord,
)
from utils.converters import iso_timestamp


def _row_to_dict(row: Any) -> dict[str, Any]:
    return {k: row[k] for k in row.keys()}


class DetectionRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def save(self, record: DetectionRecord) -> None:
        self._db.execute(
            """
            INSERT OR REPLACE INTO detections
                (frame_id, timestamp, unix_ts, detection_json,
                 alert_triggered, object_count)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                record.frame_id,
                iso_timestamp(record.timestamp),
                record.unix_ts,
                record.detection_json,
                int(record.alert_triggered),
                record.object_count,
            ),
        )

    def latest(self) -> dict[str, Any] | None:
        row = self._db.fetch_one("SELECT * FROM detections ORDER BY unix_ts DESC LIMIT 1")
        return _row_to_dict(row) if row else None

    def latest_with_alert(self) -> dict[str, Any] | None:
        row = self._db.fetch_one(
            "SELECT * FROM detections WHERE alert_triggered = 1 " "ORDER BY unix_ts DESC LIMIT 1"
        )
        return _row_to_dict(row) if row else None

    def since(self, unix_ts: int, limit: int = 500) -> list[dict[str, Any]]:
        rows = self._db.fetch_all(
            "SELECT * FROM detections WHERE unix_ts >= ? " "ORDER BY unix_ts DESC LIMIT ?",
            (unix_ts, limit),
        )
        return [_row_to_dict(r) for r in rows]

    def delete_older_than(self, unix_ts: int) -> int:
        cursor = self._db.execute("DELETE FROM detections WHERE unix_ts < ?", (unix_ts,))
        return cursor.rowcount


class LocationRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def save(self, record: LocationRecord) -> None:
        self._db.execute(
            """
            INSERT OR REPLACE INTO locations
                (location_id, timestamp, unix_ts, latitude, longitude,
                 altitude, accuracy, speed, location_json, geohash,
                 is_home, is_work, dwell_time_minutes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.location_id,
                iso_timestamp(record.timestamp),
                record.unix_ts,
                record.latitude,
                record.longitude,
                record.altitude,
                record.accuracy,
                record.speed,
                record.location_json,
                record.geohash,
                int(record.is_home),
                int(record.is_work),
                record.dwell_time_minutes,
            ),
        )

    def latest(self) -> dict[str, Any] | None:
        row = self._db.fetch_one("SELECT * FROM locations ORDER BY unix_ts DESC LIMIT 1")
        return _row_to_dict(row) if row else None

    def since(self, unix_ts: int, limit: int = 1000) -> list[dict[str, Any]]:
        rows = self._db.fetch_all(
            "SELECT * FROM locations WHERE unix_ts >= ? " "ORDER BY unix_ts ASC LIMIT ?",
            (unix_ts, limit),
        )
        return [_row_to_dict(r) for r in rows]

    def delete_older_than(self, unix_ts: int) -> int:
        cursor = self._db.execute("DELETE FROM locations WHERE unix_ts < ?", (unix_ts,))
        return cursor.rowcount


class BatteryRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def save(self, record: BatteryRecord) -> None:
        self._db.execute(
            """
            INSERT INTO battery_status
                (timestamp, unix_ts, voltage, current, percentage,
                 temperature, health_status, status_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                iso_timestamp(record.timestamp),
                record.unix_ts,
                record.voltage,
                record.current,
                record.percentage,
                record.temperature,
                record.health_status,
                record.status_json,
            ),
        )

    def latest(self) -> dict[str, Any] | None:
        row = self._db.fetch_one("SELECT * FROM battery_status ORDER BY unix_ts DESC LIMIT 1")
        return _row_to_dict(row) if row else None

    def since(self, unix_ts: int) -> list[dict[str, Any]]:
        rows = self._db.fetch_all(
            "SELECT * FROM battery_status WHERE unix_ts >= ? " "ORDER BY unix_ts ASC",
            (unix_ts,),
        )
        return [_row_to_dict(r) for r in rows]

    def delete_older_than(self, unix_ts: int) -> int:
        cursor = self._db.execute("DELETE FROM battery_status WHERE unix_ts < ?", (unix_ts,))
        return cursor.rowcount


class CommandRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def save(self, record: CommandRecord) -> None:
        self._db.execute(
            """
            INSERT OR REPLACE INTO commands
                (command_id, timestamp, command_type, params_json,
                 sent_to_esp32, ack_received, execution_time_ms)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.command_id,
                iso_timestamp(record.timestamp),
                record.command_type,
                record.params_json,
                int(record.sent_to_esp32),
                int(record.ack_received),
                record.execution_time_ms,
            ),
        )

    def latest(self, limit: int = 50) -> list[dict[str, Any]]:
        rows = self._db.fetch_all(
            "SELECT * FROM commands ORDER BY timestamp DESC LIMIT ?",
            (limit,),
        )
        return [_row_to_dict(r) for r in rows]


class MessageRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def save(self, record: MessageRecord) -> None:
        self._db.execute(
            """
            INSERT OR REPLACE INTO messages
                (message_id, timestamp, text, priority, tts_engine,
                 estimated_speak_time_ms, delivered, delivered_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.message_id,
                iso_timestamp(record.timestamp),
                record.text,
                record.priority,
                record.tts_engine,
                record.estimated_speak_time_ms,
                int(record.delivered),
                iso_timestamp(record.delivered_at) if record.delivered_at else None,
            ),
        )

    def mark_delivered(self, message_id: str) -> None:
        self._db.execute(
            "UPDATE messages SET delivered = 1, delivered_at = ? " "WHERE message_id = ?",
            (iso_timestamp(), message_id),
        )

    def history(self, limit: int = 20) -> list[dict[str, Any]]:
        rows = self._db.fetch_all(
            "SELECT * FROM messages ORDER BY timestamp DESC LIMIT ?",
            (limit,),
        )
        return [_row_to_dict(r) for r in rows]


class AlertRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def save(self, record: AlertRecord) -> None:
        self._db.execute(
            """
            INSERT OR REPLACE INTO alerts
                (alert_id, timestamp, alert_type, severity, detection_id,
                 location_latitude, location_longitude, alert_json,
                 acknowledged)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.alert_id,
                iso_timestamp(record.timestamp),
                record.alert_type,
                record.severity,
                record.detection_id,
                record.location_latitude,
                record.location_longitude,
                record.alert_json,
                int(record.acknowledged),
            ),
        )

    def latest(self, limit: int = 20) -> list[dict[str, Any]]:
        rows = self._db.fetch_all(
            "SELECT * FROM alerts ORDER BY timestamp DESC LIMIT ?",
            (limit,),
        )
        return [_row_to_dict(r) for r in rows]


class SessionRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def save(self, record: SessionRecord) -> None:
        self._db.execute(
            """
            INSERT OR REPLACE INTO sessions
                (session_id, start_time, end_time, duration_minutes,
                 distance_km, detection_count, alert_count, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.session_id,
                iso_timestamp(record.start_time),
                iso_timestamp(record.end_time) if record.end_time else None,
                record.duration_minutes,
                record.distance_km,
                record.detection_count,
                record.alert_count,
                record.metadata_json,
            ),
        )

    def current(self) -> dict[str, Any] | None:
        row = self._db.fetch_one(
            "SELECT * FROM sessions WHERE end_time IS NULL " "ORDER BY start_time DESC LIMIT 1"
        )
        return _row_to_dict(row) if row else None


class ElectricalRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def save(self, record: ElectricalRecord) -> None:
        self._db.execute(
            """
            INSERT INTO electrical_log
                (timestamp, battery_voltage_v, battery_current_ma,
                 battery_percentage, rpi_temp_c, esp32_temp_c,
                 wifi_signal_strength_db, detection_fps, inference_time_ms,
                 memory_usage_mb, memory_usage_percent, uptime_seconds)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
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
                record.memory_usage_percent,
                record.uptime_seconds,
            ),
        )

    def recent(self, limit: int = 1000) -> list[dict[str, Any]]:
        rows = self._db.fetch_all(
            "SELECT * FROM electrical_log ORDER BY timestamp DESC LIMIT ?",
            (limit,),
        )
        return [_row_to_dict(r) for r in rows]


def encode_json(payload: dict[str, Any]) -> str:
    """Helper used by services when building *_json columns."""
    return json.dumps(payload, separators=(",", ":"), default=str)
