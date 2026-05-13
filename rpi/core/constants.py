"""Hardware-independent constants. Define once, reference everywhere."""

from __future__ import annotations

from typing import Final

from core.types import BuzzerTone, ObjectClass, VibrationPattern

VIBRATION_PATTERNS: Final[dict[ObjectClass, VibrationPattern]] = {
    ObjectClass.PERSON: VibrationPattern(
        name="single_pulse", intensity=255, duration_ms=200, pulses=1
    ),
    ObjectClass.CAR: VibrationPattern(
        name="double_pulse", intensity=200, duration_ms=150, pulses=2, gap_ms=100
    ),
    ObjectClass.BICYCLE: VibrationPattern(
        name="triple_pulse", intensity=180, duration_ms=100, pulses=3, gap_ms=50
    ),
    ObjectClass.MOTORCYCLE: VibrationPattern(
        name="triple_pulse", intensity=180, duration_ms=100, pulses=3, gap_ms=50
    ),
    ObjectClass.STAIRS: VibrationPattern(name="steady", intensity=220, duration_ms=500, pulses=1),
    ObjectClass.OVERHEAD: VibrationPattern(name="steady", intensity=220, duration_ms=500, pulses=1),
    ObjectClass.OBSTACLE: VibrationPattern(
        name="slow_pulse", intensity=150, duration_ms=300, pulses=2, gap_ms=200
    ),
    ObjectClass.UNKNOWN: VibrationPattern(
        name="slow_pulse", intensity=150, duration_ms=300, pulses=2, gap_ms=200
    ),
}


BUZZER_TONES: Final[dict[str, BuzzerTone]] = {
    "standard_alert": BuzzerTone("standard_alert", 1000, 200),
    "elevation_alert": BuzzerTone("elevation_alert", 1500, 300),
    "emergency_sos": BuzzerTone("emergency_sos", 2500, 500, pattern_count=3, gap_ms=200),
    "battery_warning": BuzzerTone("battery_warning", 800, 100, pattern_count=3, gap_ms=50),
    "message_received": BuzzerTone("message_received", 2000, 300),
    "wifi_good": BuzzerTone("wifi_good", 1200, 100),
    "wifi_weak": BuzzerTone("wifi_weak", 1000, 200),
    "wifi_disconnected": BuzzerTone("wifi_disconnected", 800, 500),
}


DISTANCE_THRESHOLDS_M: Final[dict[ObjectClass, float]] = {
    ObjectClass.PERSON: 2.0,
    ObjectClass.CAR: 3.0,
    ObjectClass.BICYCLE: 2.5,
    ObjectClass.MOTORCYCLE: 2.5,
    ObjectClass.STAIRS: 1.0,
    ObjectClass.OVERHEAD: 0.5,
    ObjectClass.OBSTACLE: 1.5,
    ObjectClass.UNKNOWN: 1.5,
}


BATTERY_WARNING_THRESHOLDS: Final[tuple[int, ...]] = (50, 25, 10)

BATTERY_WARNING_MESSAGES: Final[dict[int, str]] = {
    50: "Battery at 50 percent. Consider charging.",
    25: "Battery at 25 percent. Charging recommended soon.",
    10: "Battery critically low at 10 percent.",
}


QUICK_MESSAGES: Final[tuple[str, ...]] = (
    "I'm on my way!",
    "Stay where you are",
    "Call me when you can",
    "Are you okay?",
    "I'll be there soon",
    "Take a break",
)


# YOLO COCO classes mapped to our internal ObjectClass enum.
YOLO_CLASS_MAP: Final[dict[str, ObjectClass]] = {
    "person": ObjectClass.PERSON,
    "bicycle": ObjectClass.BICYCLE,
    "car": ObjectClass.CAR,
    "motorcycle": ObjectClass.MOTORCYCLE,
    "bus": ObjectClass.CAR,
    "truck": ObjectClass.CAR,
    "train": ObjectClass.CAR,
}


MAX_MESSAGE_LENGTH: Final[int] = 500
MAX_VIBRATION_INTENSITY: Final[int] = 255
MIN_BUZZER_FREQUENCY: Final[int] = 100
MAX_BUZZER_FREQUENCY: Final[int] = 5000


RETENTION_DAYS: Final[dict[str, int]] = {
    "detections": 7,
    "locations": 7,
    "battery_status": 7,
    "commands": 7,
    "messages": 7,
    "electrical_log": 7,
    "alerts": 30,
    "sessions": 30,
    "sensor_health": 30,
}
