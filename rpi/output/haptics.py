"""Vibration motor control via the ESP32 SPI command packet.

The firmware owns vibration timing and intensity — the RPi can only send
the coarse ``vibrator_cmd`` override (0 = off, 1 = on) defined by
``rpi_to_esp_t``. Intensity and duration from the higher layers cannot be
honoured by the hardware path; they are kept in the API surface for
logging and for the no-link fallback only.
"""

from __future__ import annotations

from core.constants import MAX_VIBRATION_INTENSITY
from core.types import VibrationPattern
from sensors.esp32_spi import Esp32SpiLink
from utils.logger import get_logger
from utils.validators import clamp

_VIBRATOR_ON = 1
_VIBRATOR_OFF = 0


class HapticsController:
    """Sends the vibrator override to the ESP32 over SPI."""

    def __init__(self, link: Esp32SpiLink | None = None) -> None:
        self._link = link
        self._log = get_logger("output.haptics")

    def vibrate(self, intensity: int, duration_ms: int) -> bool:
        """Drive the motor on (intensity > 0) or off via the SPI command.

        The firmware cannot vary intensity or honour ``duration_ms`` from
        an override — it runs its own pulse timing.
        """
        intensity = int(clamp(intensity, 0, MAX_VIBRATION_INTENSITY))
        duration_ms = max(0, int(duration_ms))
        cmd = _VIBRATOR_ON if intensity > 0 else _VIBRATOR_OFF
        if self._link is None:
            self._log.info(
                "haptics(no link) intensity=%d duration=%dms -> vib_cmd=%d",
                intensity,
                duration_ms,
                cmd,
            )
            return True
        return self._link.send_command(buzzer_cmd=0, vibrator_cmd=cmd)

    def play_pattern(self, pattern: VibrationPattern) -> bool:
        """Trigger the motor for a pattern.

        The firmware runs the actual pulse sequence; the RPi only asserts
        the on override, so the pattern's pulse/gap shape is advisory.
        """
        return self.vibrate(pattern.intensity, pattern.duration_ms)
