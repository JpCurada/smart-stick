"""Vibration motor control via the ESP32 SPI command packet.

The firmware owns vibration timing. The RPi can only assert the coarse
``vibrator_cmd`` override (0 = off, 1 = on) in ``rpi_to_esp_t``, and the
firmware honours **only** the ON override: it cannot receive a standalone
OFF. The OFF frame (both command bytes zero) is indistinguishable from the
idle "no override" frame, which the firmware's SPI ISR discards.

That is fine, because the firmware re-runs its own ``vibrator_update()``
every loop *before* applying the override. When the RPi stops asserting ON,
the firmware's own pulse logic reclaims the motor pin on the next loop and
turns it off when no LiDAR obstacle is in range. So the RPi asserts ON for a
detection alert and then simply stops — it must NOT (and cannot) latch the
motor on, which previously caused constant vibration.

Intensity and duration cannot be honoured on the hardware path; they are
kept in the API surface for logging and the no-link fallback only.
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
    """Asserts the vibrator ON override to the ESP32 over SPI.

    Never sends a standalone OFF: the firmware cannot receive one (the OFF
    frame looks like the idle frame it discards), and it does not need one —
    its own ``vibrator_update()`` turns the motor off once the RPi stops
    asserting ON.
    """

    def __init__(self, link: Esp32SpiLink | None = None) -> None:
        self._link = link
        self._log = get_logger("output.haptics")

    def vibrate(self, intensity: int, duration_ms: int) -> bool:
        """Assert the motor-on override for a detection alert.

        ``intensity > 0`` asserts ON for one command; ``intensity == 0`` is a
        no-op (there is no usable OFF command — see module docstring).
        ``duration_ms`` is advisory: the firmware runs its own pulse timing.
        """
        intensity = int(clamp(intensity, 0, MAX_VIBRATION_INTENSITY))
        duration_ms = max(0, int(duration_ms))
        if intensity <= 0:
            # No standalone OFF exists; the firmware self-clears the motor.
            self._log.debug("haptics: intensity=0 is a no-op (firmware self-clears)")
            return True
        if self._link is None:
            self._log.info(
                "haptics(no link) intensity=%d duration=%dms -> vib_cmd=%d",
                intensity,
                duration_ms,
                _VIBRATOR_ON,
            )
            return True
        return self._link.send_command(buzzer_cmd=0, vibrator_cmd=_VIBRATOR_ON)

    def play_pattern(self, pattern: VibrationPattern) -> bool:
        """Trigger the motor for a pattern.

        The RPi can only assert the on override; the firmware runs the actual
        pulse sequence, so the pattern's pulse/gap shape is advisory.
        """
        return self.vibrate(pattern.intensity, pattern.duration_ms)
