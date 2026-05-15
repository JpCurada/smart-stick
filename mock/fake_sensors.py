"""Fake sensor implementations for Windows development.

Each class satisfies the SensorBase interface and returns deterministic but
slowly-varying data so the mobile app sees realistic behaviour without any
hardware present.
"""
from __future__ import annotations

import math
import random
import time
from typing import Any

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_START = time.monotonic()


def _elapsed() -> float:
    return time.monotonic() - _START


def _drift(base: float, amplitude: float, period_s: float = 60.0) -> float:
    """Sinusoidal drift around a base value."""
    return base + amplitude * math.sin(2 * math.pi * _elapsed() / period_s)


# ---------------------------------------------------------------------------
# Fake GPS — walks slowly north-east from Quezon City
# ---------------------------------------------------------------------------

class FakeGps:
    """Returns a GPS fix that drifts a few metres over time."""

    name = "gps"

    def initialize(self) -> None: ...
    def is_healthy(self) -> bool: return True
    def close(self) -> None: ...

    def read(self) -> object:
        from core.types import SensorReading
        from utils.converters import now_utc

        elapsed = _elapsed()
        lat = 14.5995 + elapsed * 0.000005   # ~0.5 m/s northward
        lon = 120.9842 + elapsed * 0.000003
        return SensorReading(
            sensor_name=self.name,
            timestamp=now_utc(),
            data={
                "latitude": round(lat, 6),
                "longitude": round(lon, 6),
                "altitude": 12.0,
                "accuracy_m": 5.0 + random.uniform(-1, 1),
                "speed": 1.2 + random.uniform(-0.2, 0.2),
                "fix_quality": 1,
            },
            healthy=True,
        )


# ---------------------------------------------------------------------------
# Fake Battery — drains from 100 % over ~4 hours
# ---------------------------------------------------------------------------

class FakeBattery:
    """Simulates a 10 Ah Li-Ion pack draining at ~2.5 A."""

    name = "battery"
    _DRAIN_PCT_PER_S = 100.0 / (4 * 3600)   # 100 % in 4 h

    def initialize(self) -> None: ...
    def is_healthy(self) -> bool: return True
    def close(self) -> None: ...

    def read(self) -> object:
        from core.types import SensorReading
        from utils.converters import now_utc

        pct = max(0, 100 - _elapsed() * self._DRAIN_PCT_PER_S)
        voltage = 3.3 + (4.2 - 3.3) * pct / 100.0
        health = "good" if pct > 80 else ("warning" if pct > 20 else "critical")
        return SensorReading(
            sensor_name=self.name,
            timestamp=now_utc(),
            data={
                "voltage_v": round(voltage, 3),
                "current_ma": 2500,
                "percentage": int(pct),
                "temperature_c": round(_drift(38.0, 3.0, period_s=300), 1),
                "health": health,
            },
            healthy=True,
        )


# ---------------------------------------------------------------------------
# Fake LIDAR — oscillates between 0.5 m and 4 m to simulate walking
# ---------------------------------------------------------------------------

class FakeLidar:
    name = "lidar"

    def initialize(self) -> None: ...
    def is_healthy(self) -> bool: return True
    def close(self) -> None: ...

    def read(self) -> object:
        from core.types import SensorReading
        from utils.converters import now_utc

        dist = abs(_drift(2.0, 1.5, period_s=8.0)) + 0.3
        return SensorReading(
            sensor_name=self.name,
            timestamp=now_utc(),
            data={"distance_m": round(dist, 2), "signal_strength": 800},
            healthy=True,
        )


# ---------------------------------------------------------------------------
# Fake Ultrasonic — alternates between clear and close readings
# ---------------------------------------------------------------------------

class FakeUltrasonic:
    """Always returns a safe distance so overhead/stairs alerts don't flood the queue."""

    def __init__(self, name: str) -> None:
        self.name = name

    def initialize(self) -> None: ...
    def is_healthy(self) -> bool: return True
    def close(self) -> None: ...

    def read(self) -> object:
        from core.types import SensorReading
        from utils.converters import now_utc

        # Fixed safe distance — well above the 0.5 m overhead / 0.3 m stairs thresholds.
        return SensorReading(
            sensor_name=self.name,
            timestamp=now_utc(),
            data={"distance_m": 2.0},
            healthy=True,
        )


# ---------------------------------------------------------------------------
# Fake ESP32 bridge — always confirms commands
# ---------------------------------------------------------------------------

class FakeEsp32Bridge:
    name = "esp32_bridge"
    _initialized = False

    def initialize(self) -> None:
        self._initialized = True

    def is_healthy(self) -> bool: return True
    def close(self) -> None: ...

    def send_vibration(self, intensity: int, duration_ms: int) -> bool:
        return True

    def send_buzz(self, frequency_hz: int, duration_ms: int) -> bool:
        return True

    def request_battery_status(self) -> dict[str, Any]:
        pct = max(0, 100 - _elapsed() * FakeBattery._DRAIN_PCT_PER_S)
        v = 3.3 + (4.2 - 3.3) * pct / 100.0
        return {
            "voltage_v": round(v, 3),
            "current_ma": 2500,
            "percentage": int(pct),
            "temperature_c": 38.0,
        }

    def read(self) -> object:
        from core.types import SensorReading
        from utils.converters import now_utc
        return SensorReading(
            sensor_name=self.name,
            timestamp=now_utc(),
            data={"connected": True},
            healthy=True,
        )


# ---------------------------------------------------------------------------
# Fake YOLO detector — emits random detections so alerts fire periodically
# ---------------------------------------------------------------------------

class FakeYoloDetector:
    """Emits a fake detection every ~8 seconds to exercise the alert pipeline."""

    _INTERVAL_S = 8.0
    _last_detection_s: float = 0.0

    def load(self) -> bool: return True

    def predict(self, frame: Any) -> list:
        from detection.yolo_model import YoloPrediction
        from core.types import ObjectClass

        now = time.monotonic()
        if (now - self._last_detection_s) < self._INTERVAL_S:
            return []
        self._last_detection_s = now

        classes = [
            ObjectClass.PERSON,
            ObjectClass.CAR,
            ObjectClass.BICYCLE,
            ObjectClass.OBSTACLE,
        ]
        obj = random.choice(classes)
        confidence = round(random.uniform(0.55, 0.97), 2)
        return [
            YoloPrediction(
                object_class=obj,
                raw_class_name=obj.value,
                confidence=confidence,
                bbox=(100, 100, 300, 400),
                distance_estimate_m=round(random.uniform(0.5, 3.5), 1),
            )
        ]


# ---------------------------------------------------------------------------
# Fake Speaker — returns instantly so the output queue never backs up
# ---------------------------------------------------------------------------

class FakeSpeaker:
    """Drop-in replacement for SpeakerController that does not block."""

    _RATE_WPM = 180

    def speak(self, text: str, priority: str = "normal") -> bool:
        return True

    def estimate_duration_ms(self, text: str) -> int:
        word_count = max(1, len(text.split()))
        return int(word_count / (self._RATE_WPM / 60.0) * 1000)


# ---------------------------------------------------------------------------
# Fake Camera — returns a black frame (no OpenCV needed)
# ---------------------------------------------------------------------------

class FakeCamera:
    name = "camera"
    _initialized = False

    def initialize(self) -> None:
        self._initialized = True

    def is_healthy(self) -> bool: return self._initialized
    def close(self) -> None: ...

    def read(self) -> object:
        from core.types import SensorReading
        from utils.converters import now_utc
        return SensorReading(
            sensor_name=self.name,
            timestamp=now_utc(),
            data={"frame": None, "width": 640, "height": 480},
            healthy=True,
        )
