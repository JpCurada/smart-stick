"""TF Mini-S LIDAR over I2C."""

from __future__ import annotations

from typing import Any

from core.config import Config
from sensors.base import SensorBase

try:
    from smbus2 import SMBus  # type: ignore[import-not-found]

    _SMBUS_AVAILABLE = True
except Exception:  # pragma: no cover
    SMBus = None  # type: ignore[assignment]
    _SMBUS_AVAILABLE = False


_LIDAR_REGISTER_DISTANCE = 0x00
_LIDAR_READ_BYTES = 7


class LidarSensor(SensorBase):
    """Forward-facing distance sensor (0.3 - 40 m)."""

    name = "lidar"

    def __init__(
        self,
        bus: int | None = None,
        address: int | None = None,
    ) -> None:
        super().__init__()
        self._bus_id = bus if bus is not None else Config.LIDAR_I2C_BUS
        self._address = address if address is not None else Config.LIDAR_I2C_ADDRESS
        self._bus: Any = None

    def _initialize_impl(self) -> None:
        if not _SMBUS_AVAILABLE:
            self._require(False, "smbus2 is not installed")
        self._bus = SMBus(self._bus_id)  # type: ignore[union-attr]

    def _read_impl(self) -> dict[str, Any]:
        self._require(self._bus is not None, "lidar not initialized")
        data = self._bus.read_i2c_block_data(
            self._address, _LIDAR_REGISTER_DISTANCE, _LIDAR_READ_BYTES
        )
        distance_cm = data[0] | (data[1] << 8)
        strength = data[2] | (data[3] << 8)
        return {
            "distance_m": distance_cm / 100.0,
            "signal_strength": strength,
        }

    def _close_impl(self) -> None:
        if self._bus is not None:
            self._bus.close()
            self._bus = None
