"""Battery voltage / percentage sensor.

In production the ESP32 reports battery state over UART; this class queries
the bridge. When no bridge is available it simulates a slowly draining
battery so the rest of the system can be exercised end-to-end.
"""

from __future__ import annotations

import time
from typing import Any

from core.types import HealthStatus
from sensors.base import SensorBase
from sensors.esp32_bridge import Esp32Bridge

_MIN_VOLTAGE = 3.3
_MAX_VOLTAGE = 4.2


def voltage_to_percentage(voltage: float) -> int:
    """Linear approximation of Li-Ion charge curve. Clamped to 0-100."""
    if voltage <= _MIN_VOLTAGE:
        return 0
    if voltage >= _MAX_VOLTAGE:
        return 100
    ratio = (voltage - _MIN_VOLTAGE) / (_MAX_VOLTAGE - _MIN_VOLTAGE)
    return int(round(ratio * 100))


def classify_health(percentage: int, voltage: float, temperature_c: float) -> HealthStatus:
    if percentage < 20 or voltage < 3.5 or temperature_c > 55.0:
        return HealthStatus.CRITICAL
    if percentage < 80 or voltage < 4.5 or temperature_c > 45.0:
        return HealthStatus.WARNING
    return HealthStatus.GOOD


class BatterySensor(SensorBase):
    """Battery telemetry source."""

    name = "battery"

    def __init__(self, bridge: Esp32Bridge | None = None) -> None:
        super().__init__()
        self._bridge = bridge
        self._fake_start = time.monotonic()

    def _initialize_impl(self) -> None:
        if self._bridge is not None:
            self._bridge.initialize()

    def _read_impl(self) -> dict[str, Any]:
        if self._bridge is not None and self._bridge.is_healthy():
            payload = self._bridge.request_battery_status()
        else:
            payload = self._fake_payload()

        voltage = float(payload.get("voltage_v", 0.0))
        percentage = int(payload.get("percentage", voltage_to_percentage(voltage)))
        current_ma = payload.get("current_ma")
        temperature_c = float(payload.get("temperature_c", 35.0))
        health = classify_health(percentage, voltage, temperature_c)

        return {
            "voltage_v": voltage,
            "current_ma": current_ma,
            "percentage": percentage,
            "temperature_c": temperature_c,
            "health": health.value,
        }

    def _fake_payload(self) -> dict[str, Any]:
        elapsed_min = (time.monotonic() - self._fake_start) / 60.0
        percentage = max(0, int(100 - elapsed_min * 0.5))
        voltage = _MIN_VOLTAGE + (_MAX_VOLTAGE - _MIN_VOLTAGE) * (percentage / 100.0)
        return {
            "voltage_v": round(voltage, 2),
            "current_ma": 2000,
            "percentage": percentage,
            "temperature_c": 35.0,
        }
