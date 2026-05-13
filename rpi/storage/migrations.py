"""Schema migrations and retention cleanup."""

from __future__ import annotations

import time

from core.constants import RETENTION_DAYS
from storage.database import Database
from utils.logger import get_logger

_log = get_logger(__name__)


_RETENTION_TABLES: dict[str, tuple[str, str]] = {
    "detections": ("detections", "unix_ts"),
    "locations": ("locations", "unix_ts"),
    "battery_status": ("battery_status", "unix_ts"),
    "commands": ("commands", "timestamp"),
    "messages": ("messages", "timestamp"),
    "electrical_log": ("electrical_log", "timestamp"),
    "alerts": ("alerts", "timestamp"),
    "sessions": ("sessions", "start_time"),
    "sensor_health": ("sensor_health", "timestamp"),
}


def run_migrations(db: Database) -> None:
    """Create schema (idempotent). Future migrations go here."""
    db.initialize_schema()


def apply_retention(db: Database) -> dict[str, int]:
    """Delete rows older than retention windows. Returns rows removed per table."""
    deleted: dict[str, int] = {}
    now = int(time.time())
    for key, (table, column) in _RETENTION_TABLES.items():
        days = RETENTION_DAYS.get(key, 7)
        cutoff = now - (days * 86400)
        if column == "unix_ts":
            cursor = db.execute(f"DELETE FROM {table} WHERE {column} < ?", (cutoff,))
        else:
            iso_cutoff = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(cutoff))
            cursor = db.execute(f"DELETE FROM {table} WHERE {column} < ?", (iso_cutoff,))
        deleted[table] = cursor.rowcount
    _log.info("retention cleanup deleted rows: %s", deleted)
    db.vacuum()
    return deleted
