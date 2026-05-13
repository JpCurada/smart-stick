"""Pydantic models — single source of truth for record shapes."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class DetectionRecord(BaseModel):
    frame_id: str
    timestamp: datetime
    unix_ts: int
    detection_json: str
    alert_triggered: bool = False
    object_count: int = 0


class LocationRecord(BaseModel):
    location_id: str
    timestamp: datetime
    unix_ts: int
    latitude: float
    longitude: float
    altitude: float | None = None
    accuracy: float | None = None
    speed: float | None = None
    location_json: str
    geohash: str | None = None
    is_home: bool = False
    is_work: bool = False
    dwell_time_minutes: int | None = None


class BatteryRecord(BaseModel):
    timestamp: datetime
    unix_ts: int
    voltage: float
    current: int | None = None
    percentage: int = Field(ge=0, le=100)
    temperature: float | None = None
    health_status: str
    status_json: str


class CommandRecord(BaseModel):
    command_id: str
    timestamp: datetime
    command_type: str
    params_json: str
    sent_to_esp32: bool = False
    ack_received: bool = False
    execution_time_ms: int | None = None


class MessageRecord(BaseModel):
    message_id: str
    timestamp: datetime
    text: str = Field(max_length=500)
    priority: str = "normal"
    tts_engine: str | None = None
    estimated_speak_time_ms: int | None = None
    delivered: bool = False
    delivered_at: datetime | None = None


class AlertRecord(BaseModel):
    alert_id: str
    timestamp: datetime
    alert_type: str
    severity: str
    detection_id: str | None = None
    location_latitude: float | None = None
    location_longitude: float | None = None
    alert_json: str
    acknowledged: bool = False


class SessionRecord(BaseModel):
    session_id: str
    start_time: datetime
    end_time: datetime | None = None
    duration_minutes: int | None = None
    distance_km: float | None = None
    detection_count: int = 0
    alert_count: int = 0
    metadata_json: str | None = None


class ElectricalRecord(BaseModel):
    timestamp: datetime
    battery_voltage_v: float
    battery_current_ma: int | None = None
    battery_percentage: int | None = None
    rpi_temp_c: float | None = None
    esp32_temp_c: float | None = None
    wifi_signal_strength_db: int | None = None
    detection_fps: float | None = None
    inference_time_ms: int | None = None
    memory_usage_mb: int | None = None
    memory_usage_percent: float | None = None
    uptime_seconds: int | None = None


__all__ = [
    "DetectionRecord",
    "LocationRecord",
    "BatteryRecord",
    "CommandRecord",
    "MessageRecord",
    "AlertRecord",
    "SessionRecord",
    "ElectricalRecord",
]


# Convenience alias used by repositories when callers want a dict of any record.
RecordLike = dict[str, Any]
