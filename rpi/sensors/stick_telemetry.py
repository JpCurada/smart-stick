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

import threading
import time
from typing import Any

from core.config import Config
from sensors.base import SensorBase
from sensors.esp32_spi import Esp32SpiLink

# Readers within this window share the most recent decoded frame instead of
# each forcing its own SPI transfer. This sensor is polled by three threads
# (detection ~6 Hz, location 5 s, SOS watcher 0.5 s); without coherence each
# transfer's fresh frame would be seen by only one of them, so a one-shot
# flag like sos_active could be consumed by the detection thread and missed
# entirely by the SOS watcher. A short coherence window keeps all readers on
# the same latest frame so the SOS flag is observed regardless of caller.
_FRAME_COHERENCE_S = 0.1


class StickTelemetrySensor(SensorBase):
    """Single source of truth for ESP32-hosted physical sensors.

    :meth:`read` returns the most recent decoded telemetry packet, shared
    coherently across the threads that poll it. A new SPI transfer is taken
    only when the cached frame is older than ``_FRAME_COHERENCE_S``; within
    that window concurrent readers see the same frame. When no packet has
    arrived within ``ESP32_FRAME_TIMEOUT_S`` the reading is reported
    unhealthy so callers fall back gracefully. Thread-safe.
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
        self._last_transfer_at: float = 0.0
        self._lock = threading.Lock()

    def _initialize_impl(self) -> None:
        self._link.open()
        self._require(self._link.available, "ESP32 SPI link unavailable")

    def _read_impl(self) -> dict[str, Any]:
        with self._lock:
            now = time.monotonic()
            # Only take a fresh transfer if the cached frame is outside the
            # coherence window. An all-zero command frame means "no override"
            # — the firmware keeps driving its own outputs while we read.
            if now - self._last_transfer_at >= _FRAME_COHERENCE_S:
                self._last_transfer_at = now
                frame = self._link.transfer()
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
