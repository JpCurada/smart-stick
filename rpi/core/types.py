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
    BICYCLE = "bicycle"
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


class SpeechPriority(str, Enum):
    """Earpiece preemption hierarchy. Lower value = higher priority."""

    GUARDIAN = "guardian"  # P1: from guardian via mobile app; preempts everything
    LSTM = "lstm"  # P2: movement analyzer narration
    DETECTION = "detection"  # P3: detection alert TTS

    @property
    def rank(self) -> int:
        return _SPEECH_PRIORITY_RANK[self]


_SPEECH_PRIORITY_RANK: dict[SpeechPriority, int] = {
    SpeechPriority.GUARDIAN: 0,
    SpeechPriority.LSTM: 1,
    SpeechPriority.DETECTION: 2,
}


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
    # Where distance_m came from: "lidar" (firmware forward LiDAR), "camera"
    # (YOLO estimate), or "ultrasonic" (firmware overhead/drop flag). The
    # firmware drives the motor itself for forward LiDAR obstacles, so the
    # RPi suppresses its own vibration only when distance_source == "lidar"
    # to avoid double-driving the motor for the same obstacle.
    distance_source: str | None = None


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
