"""HC-SR04 ultrasonic distance sensor.

Used twice on the stick: one pointing up (overhead obstacles) and one
pointing down (stairs / curbs).
"""

from __future__ import annotations

import time
from typing import Any

from sensors.base import SensorBase

try:
    import RPi.GPIO as GPIO  # type: ignore[import-not-found]

    _GPIO_AVAILABLE = True
except Exception:  # pragma: no cover
    GPIO = None  # type: ignore[assignment]
    _GPIO_AVAILABLE = False


_SPEED_OF_SOUND_M_S: float = 343.0
_PULSE_S: float = 0.00001
_MAX_ECHO_WAIT_S: float = 0.04


class UltrasonicSensor(SensorBase):
    """Single HC-SR04 sensor on dedicated trigger/echo GPIO pins."""

    def __init__(self, name: str, trigger_pin: int, echo_pin: int) -> None:
        self.name = name
        super().__init__()
        self._trigger_pin = trigger_pin
        self._echo_pin = echo_pin

    def _initialize_impl(self) -> None:
        if not _GPIO_AVAILABLE:
            self._require(False, "RPi.GPIO is not installed")
        GPIO.setmode(GPIO.BCM)  # type: ignore[union-attr]
        GPIO.setup(self._trigger_pin, GPIO.OUT)  # type: ignore[union-attr]
        GPIO.setup(self._echo_pin, GPIO.IN)  # type: ignore[union-attr]
        GPIO.output(self._trigger_pin, False)  # type: ignore[union-attr]
        time.sleep(0.05)

    def _read_impl(self) -> dict[str, Any]:
        distance_m = self._measure_distance_m()
        return {"distance_m": distance_m}

    def _measure_distance_m(self) -> float:
        GPIO.output(self._trigger_pin, True)  # type: ignore[union-attr]
        time.sleep(_PULSE_S)
        GPIO.output(self._trigger_pin, False)  # type: ignore[union-attr]

        deadline = time.perf_counter() + _MAX_ECHO_WAIT_S
        echo_start = self._wait_for_edge(level=1, deadline=deadline)
        echo_end = self._wait_for_edge(level=0, deadline=deadline)

        elapsed_s = echo_end - echo_start
        return (elapsed_s * _SPEED_OF_SOUND_M_S) / 2.0

    def _wait_for_edge(self, level: int, deadline: float) -> float:
        while time.perf_counter() < deadline:
            if GPIO.input(self._echo_pin) == level:  # type: ignore[union-attr]
                return time.perf_counter()
        raise TimeoutError(f"{self.name} echo timeout")

    def _close_impl(self) -> None:
        if _GPIO_AVAILABLE:
            try:
                GPIO.cleanup([self._trigger_pin, self._echo_pin])  # type: ignore[union-attr]
            except Exception:
                pass
