"""ICM-20948 IMU over I2C (accelerometer + gyroscope, 9-axis)."""

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


_PWR_MGMT_1 = 0x06
_ACCEL_XOUT_H = 0x2D
_ACCEL_SENSITIVITY = 16384.0  # LSB/g at default ±2g range


def _twos_complement(high: int, low: int) -> int:
    raw = (high << 8) | low
    if raw >= 0x8000:
        raw -= 0x10000
    return raw


class ImuSensor(SensorBase):
    """Reads accelerometer values from the IMU."""

    name = "imu"

    def __init__(
        self,
        bus: int | None = None,
        address: int | None = None,
    ) -> None:
        super().__init__()
        self._bus_id = bus if bus is not None else Config.IMU_I2C_BUS
        self._address = address if address is not None else Config.IMU_I2C_ADDRESS
        self._bus: Any = None

    def _initialize_impl(self) -> None:
        if not _SMBUS_AVAILABLE:
            self._require(False, "smbus2 is not installed")
        self._bus = SMBus(self._bus_id)  # type: ignore[union-attr]
        self._bus.write_byte_data(self._address, _PWR_MGMT_1, 0x00)

    def _read_impl(self) -> dict[str, Any]:
        self._require(self._bus is not None, "imu not initialized")
        raw = self._bus.read_i2c_block_data(self._address, _ACCEL_XOUT_H, 6)
        ax = _twos_complement(raw[0], raw[1]) / _ACCEL_SENSITIVITY
        ay = _twos_complement(raw[2], raw[3]) / _ACCEL_SENSITIVITY
        az = _twos_complement(raw[4], raw[5]) / _ACCEL_SENSITIVITY
        return {
            "accel_g": {"x": ax, "y": ay, "z": az},
            "magnitude_g": (ax * ax + ay * ay + az * az) ** 0.5,
        }

    def _close_impl(self) -> None:
        if self._bus is not None:
            self._bus.close()
            self._bus = None
