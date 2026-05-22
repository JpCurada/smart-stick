"""Buzzer control via the ESP32 SPI command packet.

The firmware owns the buzzer patterns — the RPi can only select one of
the coarse ``buzzer_cmd`` modes defined by ``rpi_to_esp_t``:

    0 = off   1 = drop   2 = overhead   3 = sos

Arbitrary frequency / duration from the higher layers cannot be honoured
by the hardware path; the API surface keeps them for logging and the
no-link fallback only.
"""

from __future__ import annotations

from core.constants import MAX_BUZZER_FREQUENCY, MIN_BUZZER_FREQUENCY
from core.types import BuzzerTone
from sensors.esp32_spi import Esp32SpiLink
from utils.logger import get_logger
from utils.validators import clamp

BUZZER_OFF = 0
BUZZER_DROP = 1
BUZZER_OVERHEAD = 2
BUZZER_SOS = 3

# Named tones (core/constants.py) mapped to firmware buzzer modes. The
# firmware has no general-purpose beep, so non-emergency tones fall back
# to the "drop" pattern as a generic alert.
_TONE_TO_CMD: dict[str, int] = {
    "emergency_sos": BUZZER_SOS,
    "elevation_alert": BUZZER_OVERHEAD,
}


class BuzzerController:
    """Sends the buzzer-mode override to the ESP32 over SPI."""

    def __init__(self, link: Esp32SpiLink | None = None) -> None:
        self._link = link
        self._log = get_logger("output.buzzer")

    def buzz(self, frequency_hz: int, duration_ms: int) -> bool:
        """Trigger a generic buzzer alert.

        Frequency and duration cannot be honoured by the firmware override;
        any non-zero frequency selects the generic "drop" alert pattern.
        """
        frequency_hz = int(clamp(frequency_hz, MIN_BUZZER_FREQUENCY, MAX_BUZZER_FREQUENCY))
        duration_ms = max(0, int(duration_ms))
        cmd = BUZZER_DROP if duration_ms > 0 else BUZZER_OFF
        return self._send(cmd, f"buzz freq={frequency_hz}Hz duration={duration_ms}ms")

    def play_tone(self, tone: BuzzerTone) -> bool:
        """Play a named tone by mapping it to a firmware buzzer mode."""
        cmd = _TONE_TO_CMD.get(tone.name, BUZZER_DROP)
        return self._send(cmd, f"tone={tone.name}")

    def _send(self, buzzer_cmd: int, context: str) -> bool:
        if self._link is None:
            self._log.info("buzzer(no link) %s -> buzz_cmd=%d", context, buzzer_cmd)
            return True
        return self._link.send_command(buzzer_cmd=buzzer_cmd, vibrator_cmd=0)
