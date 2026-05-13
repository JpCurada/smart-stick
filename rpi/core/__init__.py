"""Core: configuration, constants, types, exceptions."""

from core.config import Config
from core.exceptions import (
    ConfigError,
    DetectionError,
    HardwareNotAvailable,
    OutputError,
    SensorError,
    SensorTimeoutError,
    SmartStickError,
    StorageError,
)
from core.types import (
    AlertSeverity,
    BuzzerTone,
    Coordinates,
    Detection,
    Environment,
    HealthStatus,
    ObjectClass,
    SensorReading,
    VibrationPattern,
)

__all__ = [
    "Config",
    "SmartStickError",
    "SensorError",
    "SensorTimeoutError",
    "HardwareNotAvailable",
    "DetectionError",
    "StorageError",
    "OutputError",
    "ConfigError",
    "Environment",
    "ObjectClass",
    "AlertSeverity",
    "HealthStatus",
    "Coordinates",
    "SensorReading",
    "Detection",
    "VibrationPattern",
    "BuzzerTone",
]
