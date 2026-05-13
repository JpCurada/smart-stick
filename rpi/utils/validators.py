"""Input validation predicates."""

from __future__ import annotations

from core.constants import (
    MAX_BUZZER_FREQUENCY,
    MAX_VIBRATION_INTENSITY,
    MIN_BUZZER_FREQUENCY,
)


def is_valid_latitude(value: float) -> bool:
    return -90.0 <= value <= 90.0


def is_valid_longitude(value: float) -> bool:
    return -180.0 <= value <= 180.0


def is_valid_percentage(value: int) -> bool:
    return 0 <= value <= 100


def is_valid_intensity(value: int) -> bool:
    return 0 <= value <= MAX_VIBRATION_INTENSITY


def is_valid_frequency(value: int) -> bool:
    return MIN_BUZZER_FREQUENCY <= value <= MAX_BUZZER_FREQUENCY


def clamp(value: float, low: float, high: float) -> float:
    if value < low:
        return low
    if value > high:
        return high
    return value
