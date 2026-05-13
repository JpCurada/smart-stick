"""Buzzer tone generation via the ESP32 bridge."""

from __future__ import annotations

from core.constants import MAX_BUZZER_FREQUENCY, MIN_BUZZER_FREQUENCY
from core.exceptions import OutputError
from core.types import BuzzerTone
from sensors.esp32_bridge import Esp32Bridge
from utils.logger import get_logger
from utils.validators import clamp


class BuzzerController:
    """Sends buzzer commands to the ESP32."""

    def __init__(self, bridge: Esp32Bridge | None = None) -> None:
        self._bridge = bridge
        self._log = get_logger("output.buzzer")

    def buzz(self, frequency_hz: int, duration_ms: int) -> bool:
        frequency_hz = int(clamp(frequency_hz, MIN_BUZZER_FREQUENCY, MAX_BUZZER_FREQUENCY))
        duration_ms = max(0, int(duration_ms))
        if self._bridge is None:
            self._log.info("buzz(no bridge) freq=%dHz duration=%dms", frequency_hz, duration_ms)
            return True
        ok = self._bridge.send_buzz(frequency_hz, duration_ms)
        if not ok:
            raise OutputError("ESP32 buzz command failed")
        return True

    def play_tone(self, tone: BuzzerTone) -> bool:
        ok = True
        for _ in range(tone.pattern_count):
            ok = self.buzz(tone.frequency_hz, tone.duration_ms) and ok
            if tone.gap_ms > 0:
                self.buzz(0, tone.gap_ms)
        return ok
