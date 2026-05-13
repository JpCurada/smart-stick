"""Hardware sensor abstraction layer.

All sensors implement the SensorBase interface so that detection and
services can depend on the abstract contract rather than concrete hardware.
"""

from sensors.base import SensorBase, SensorStatus
from sensors.battery import BatterySensor
from sensors.camera import CameraSensor
from sensors.esp32_bridge import Esp32Bridge
from sensors.gps import GpsSensor
from sensors.imu import ImuSensor
from sensors.lidar import LidarSensor
from sensors.ultrasonic import UltrasonicSensor

__all__ = [
    "SensorBase",
    "SensorStatus",
    "BatterySensor",
    "CameraSensor",
    "Esp32Bridge",
    "GpsSensor",
    "ImuSensor",
    "LidarSensor",
    "UltrasonicSensor",
]
