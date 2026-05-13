"""Custom exception hierarchy for Smart Stick."""

from __future__ import annotations


class SmartStickError(Exception):
    """Base exception for all Smart Stick errors."""


class ConfigError(SmartStickError):
    """Raised when configuration is invalid or missing."""


class SensorError(SmartStickError):
    """Raised when a sensor cannot produce a valid reading."""


class SensorTimeoutError(SensorError):
    """Raised when a sensor read exceeds its timeout budget."""


class HardwareNotAvailable(SensorError):
    """Raised when required hardware libraries or devices are not present."""


class DetectionError(SmartStickError):
    """Raised when detection/inference fails."""


class StorageError(SmartStickError):
    """Raised when a persistence operation fails."""


class OutputError(SmartStickError):
    """Raised when an output command cannot be delivered."""
