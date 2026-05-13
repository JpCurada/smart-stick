"""Shared types, enums, and data models used across layers."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class Environment(str, Enum):
    DEV = "dev"
    PROD = "prod"


class ObjectClass(str, Enum):
    PERSON = "person"
    CAR = "car"
    BICYCLE = "bicycle"
    MOTORCYCLE = "motorcycle"
    STAIRS = "stairs"
    OVERHEAD = "overhead"
    OBSTACLE = "obstacle"
    UNKNOWN = "unknown"


class AlertSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class HealthStatus(str, Enum):
    GOOD = "good"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass(frozen=True)
class Coordinates:
    latitude: float
    longitude: float
    altitude: float | None = None
    accuracy_m: float | None = None


@dataclass
class SensorReading:
    """Standardized sensor read result."""

    sensor_name: str
    timestamp: datetime
    data: dict
    healthy: bool = True
    error: str | None = None


@dataclass
class Detection:
    """Single object detection result."""

    object_class: ObjectClass
    confidence: float
    distance_m: float
    bbox: tuple[int, int, int, int] | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class VibrationPattern:
    """Vibration motor pattern definition."""

    name: str
    intensity: int  # 0-255
    duration_ms: int
    pulses: int = 1
    gap_ms: int = 0


@dataclass(frozen=True)
class BuzzerTone:
    """Buzzer tone definition."""

    name: str
    frequency_hz: int  # 100-5000
    duration_ms: int
    pattern_count: int = 1
    gap_ms: int = 0
