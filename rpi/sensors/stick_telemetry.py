"""Telemetry sensor backed by the ESP32 SPI link.

The ESP32 is the sensor hub: it owns the LiDAR, both ultrasonic sensors
and the GPS, and exposes them through the SPI telemetry packet (see
:mod:`sensors.esp32_spi`). This class turns each SPI transfer into a
single :class:`~sensors.base.SensorBase` so the detection loop and the
location service can depend on the standard sensor contract instead of
talking to three separate drivers.

The firmware owns the drop / overhead / SOS decision logic; the RPi
trusts those flags rather than re-deriving them from raw distance.
"""

from __future__ import annotations

import time
from typing import Any

from core.config import Config
from sensors.base import SensorBase
from sensors.esp32_spi import Esp32SpiLink


class StickTelemetrySensor(SensorBase):
    """Single source of truth for ESP32-hosted physical sensors.

    Each :meth:`read` performs one SPI transfer and returns the decoded
    telemetry packet. When the ESP32 returns no fresh packet within
    ``ESP32_FRAME_TIMEOUT_S`` the reading is reported unhealthy so callers
    fall back gracefully.
    """

    name = "stick_telemetry"

    def __init__(
        self,
        link: Esp32SpiLink | None = None,
        frame_timeout_s: float | None = None,
    ) -> None:
        super().__init__()
        self._link = link if link is not None else Esp32SpiLink()
        self._frame_timeout_s = (
            frame_timeout_s if frame_timeout_s is not None else Config.ESP32_FRAME_TIMEOUT_S
        )
        self._last_frame: dict[str, Any] | None = None
        self._last_frame_at: float = 0.0

    def _initialize_impl(self) -> None:
        self._link.open()
        self._require(self._link.available, "ESP32 SPI link unavailable")

    def _read_impl(self) -> dict[str, Any]:
        # An all-zero command frame means "no override" — the firmware
        # keeps driving its own outputs while we just read telemetry.
        frame = self._link.transfer()
        now = time.monotonic()
        if frame is not None:
            self._last_frame = frame
            self._last_frame_at = now

        self._require(self._last_frame is not None, "no telemetry packet received yet")
        age_s = now - self._last_frame_at
        self._require(
            age_s <= self._frame_timeout_s,
            f"telemetry stale ({age_s:.1f}s old)",
        )
        return dict(self._last_frame)  # type: ignore[arg-type]

    def _close_impl(self) -> None:
        self._link.close()
