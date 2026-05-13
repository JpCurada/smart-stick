"""Vibration motor control via the ESP32 bridge."""

from __future__ import annotations

from core.constants import MAX_VIBRATION_INTENSITY
from core.exceptions import OutputError
from core.types import VibrationPattern
from sensors.esp32_bridge import Esp32Bridge
from utils.logger import get_logger
from utils.validators import clamp


class HapticsController:
    """Sends vibration commands to the ESP32."""

    def __init__(self, bridge: Esp32Bridge | None = None) -> None:
        self._bridge = bridge
        self._log = get_logger("output.haptics")

    def vibrate(self, intensity: int, duration_ms: int) -> bool:
        intensity = int(clamp(intensity, 0, MAX_VIBRATION_INTENSITY))
        duration_ms = max(0, int(duration_ms))
        if self._bridge is None:
            self._log.info("haptics(no bridge) intensity=%d duration=%dms", intensity, duration_ms)
            return True
        ok = self._bridge.send_vibration(intensity, duration_ms)
        if not ok:
            raise OutputError("ESP32 vibration command failed")
        return True

    def play_pattern(self, pattern: VibrationPattern) -> bool:
        """Execute every pulse in the pattern. Caller waits via ESP32 firmware."""
        ok = True
        for _ in range(pattern.pulses):
            ok = self.vibrate(pattern.intensity, pattern.duration_ms) and ok
            if pattern.gap_ms > 0:
                self.vibrate(0, pattern.gap_ms)
        return ok
