"""UART link to the ESP32 haptics / battery co-processor.

The ESP32 exposes a tiny line protocol:
    VIBRATE:<intensity>:<duration_ms>
    BUZZ:<frequency_hz>:<duration_ms>
    BATTERY?           -> "BATTERY:<voltage>:<current_ma>:<percentage>:<temp_c>"
    PING               -> "PONG"
"""

from __future__ import annotations

import threading
from typing import Any

from core.config import Config
from sensors.base import SensorBase

try:
    import serial  # type: ignore[import-not-found]

    _SERIAL_AVAILABLE = True
except Exception:  # pragma: no cover
    serial = None  # type: ignore[assignment]
    _SERIAL_AVAILABLE = False


class Esp32Bridge(SensorBase):
    """Serial bridge to the ESP32. Acts as a sensor (battery) AND an actuator."""

    name = "esp32_bridge"

    def __init__(
        self,
        port: str | None = None,
        baudrate: int | None = None,
        timeout_s: float = 1.0,
    ) -> None:
        super().__init__()
        self._port = port if port is not None else Config.ESP32_PORT
        self._baudrate = baudrate if baudrate is not None else Config.ESP32_BAUDRATE
        self._timeout_s = timeout_s
        self._serial: Any = None
        self._lock = threading.Lock()

    def _initialize_impl(self) -> None:
        if not _SERIAL_AVAILABLE:
            self._require(False, "pyserial is not installed")
        self._serial = serial.Serial(  # type: ignore[union-attr]
            self._port, self._baudrate, timeout=self._timeout_s
        )

    def _read_impl(self) -> dict[str, Any]:
        response = self._send("PING")
        self._require(response == "PONG", f"unexpected response: {response!r}")
        return {"connected": True}

    def send_vibration(self, intensity: int, duration_ms: int) -> bool:
        return self._send_command(f"VIBRATE:{intensity}:{duration_ms}")

    def send_buzz(self, frequency_hz: int, duration_ms: int) -> bool:
        return self._send_command(f"BUZZ:{frequency_hz}:{duration_ms}")

    def request_battery_status(self) -> dict[str, Any]:
        response = self._send("BATTERY?")
        if not response.startswith("BATTERY:"):
            return {}
        parts = response.split(":")
        if len(parts) < 5:
            return {}
        try:
            return {
                "voltage_v": float(parts[1]),
                "current_ma": int(parts[2]),
                "percentage": int(parts[3]),
                "temperature_c": float(parts[4]),
            }
        except ValueError:
            return {}

    def _send_command(self, payload: str) -> bool:
        try:
            self._send(payload)
            return True
        except Exception as exc:
            self._log.warning("ESP32 command %s failed: %s", payload, exc)
            return False

    def _send(self, payload: str) -> str:
        if not self._initialized:
            self.initialize()
        with self._lock:
            self._require(self._serial is not None, "esp32 not initialized")
            self._serial.reset_input_buffer()
            self._serial.write(f"{payload}\n".encode("ascii"))
            line = self._serial.readline().decode("ascii", errors="ignore").strip()
            return line

    def _close_impl(self) -> None:
        if self._serial is not None:
            self._serial.close()
            self._serial = None
