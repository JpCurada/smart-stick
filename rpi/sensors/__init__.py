"""Hardware sensor abstraction layer.

All sensors implement the SensorBase interface so that detection and
services can depend on the abstract contract rather than concrete hardware.
"""

from sensors.base import SensorBase, SensorStatus
from sensors.camera import CameraSensor
from sensors.esp32_spi import Esp32SpiLink
from sensors.gps import GpsSensor
from sensors.imu import ImuSensor
from sensors.lidar import LidarSensor
from sensors.stick_telemetry import StickTelemetrySensor
from sensors.ultrasonic import UltrasonicSensor

__all__ = [
    "SensorBase",
    "SensorStatus",
    "CameraSensor",
    "Esp32SpiLink",
    "GpsSensor",
    "ImuSensor",
    "LidarSensor",
    "StickTelemetrySensor",
    "UltrasonicSensor",
]
