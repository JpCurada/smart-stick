"""Single source of truth for runtime configuration.

Values are read from environment variables once at import time. All other
modules should depend on this Config class rather than reading os.environ
directly.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Final

from core.types import Environment


def _env_str(key: str, default: str) -> str:
    return os.getenv(key, default)


def _env_int(key: str, default: int) -> int:
    raw = os.getenv(key)
    return int(raw) if raw is not None and raw != "" else default


def _env_float(key: str, default: float) -> float:
    raw = os.getenv(key)
    return float(raw) if raw is not None and raw != "" else default


def _env_bool(key: str, default: bool) -> bool:
    raw = os.getenv(key)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


class Config:
    """Application configuration. Read once, used everywhere."""

    ENVIRONMENT: Final[Environment] = Environment(
        _env_str("SMART_STICK_ENV", Environment.DEV.value).lower()
    )

    PROJECT_ROOT: Final[Path] = Path(__file__).resolve().parent.parent
    DATA_DIR: Final[Path] = Path(_env_str("DATA_DIR", str(PROJECT_ROOT / "data")))
    DATABASE_PATH: Final[Path] = Path(_env_str("DATABASE_PATH", str(DATA_DIR / "smartstick.db")))
    CSV_LOG_PATH: Final[Path] = Path(
        _env_str("CSV_LOG_PATH", str(DATA_DIR / "electrical_parameters.csv"))
    )

    API_HOST: Final[str] = _env_str("API_HOST", "0.0.0.0")
    API_PORT: Final[int] = _env_int("API_PORT", 5000)
    API_CORS_ORIGINS: Final[list[str]] = [
        o.strip() for o in _env_str("API_CORS_ORIGINS", "*").split(",") if o.strip()
    ]

    LOG_LEVEL: Final[str] = _env_str("LOG_LEVEL", "INFO").upper()

    DETECTION_FPS: Final[int] = _env_int("DETECTION_FPS", 6)
    DETECTION_ENABLED: Final[bool] = _env_bool("DETECTION_ENABLED", True)
    YOLO_MODEL_PATH: Final[str] = _env_str("YOLO_MODEL_PATH", "yolov8n.pt")
    YOLO_CONFIDENCE_THRESHOLD: Final[float] = _env_float("YOLO_CONFIDENCE_THRESHOLD", 0.45)
    YOLO_IMG_SIZE: Final[int] = _env_int("YOLO_IMG_SIZE", 320)

    CAMERA_DEVICE: Final[str] = _env_str("CAMERA_DEVICE", "/dev/video0")
    CAMERA_WIDTH: Final[int] = _env_int("CAMERA_WIDTH", 320)
    CAMERA_HEIGHT: Final[int] = _env_int("CAMERA_HEIGHT", 240)

    GPS_PORT: Final[str] = _env_str("GPS_PORT", "/dev/ttyUSB0")
    GPS_BAUDRATE: Final[int] = _env_int("GPS_BAUDRATE", 9600)
    GPS_UPDATE_INTERVAL_S: Final[int] = _env_int("GPS_UPDATE_INTERVAL_S", 5)

    LIDAR_I2C_BUS: Final[int] = _env_int("LIDAR_I2C_BUS", 1)
    LIDAR_I2C_ADDRESS: Final[int] = _env_int("LIDAR_I2C_ADDRESS", 0x10)

    ULTRASONIC_OVERHEAD_TRIG_PIN: Final[int] = _env_int("ULTRASONIC_OVERHEAD_TRIG_PIN", 23)
    ULTRASONIC_OVERHEAD_ECHO_PIN: Final[int] = _env_int("ULTRASONIC_OVERHEAD_ECHO_PIN", 25)
    ULTRASONIC_DOWN_TRIG_PIN: Final[int] = _env_int("ULTRASONIC_DOWN_TRIG_PIN", 24)
    ULTRASONIC_DOWN_ECHO_PIN: Final[int] = _env_int("ULTRASONIC_DOWN_ECHO_PIN", 22)

    IMU_I2C_BUS: Final[int] = _env_int("IMU_I2C_BUS", 1)
    IMU_I2C_ADDRESS: Final[int] = _env_int("IMU_I2C_ADDRESS", 0x68)

    BATTERY_UPDATE_INTERVAL_S: Final[int] = _env_int("BATTERY_UPDATE_INTERVAL_S", 30)
    BATTERY_WARN_50: Final[bool] = _env_bool("BATTERY_WARN_50", True)
    BATTERY_WARN_25: Final[bool] = _env_bool("BATTERY_WARN_25", True)
    BATTERY_WARN_10: Final[bool] = _env_bool("BATTERY_WARN_10", True)

    # ── ESP32 SPI sensor hub ────────────────────────────────────────────
    # The ESP32 is an SPI slave; the RPi is the master. Each transfer is a
    # fixed 64-byte full-duplex frame: the ESP32 returns a 15-byte
    # esp_to_rpi_t telemetry packet, the RPi sends a 4-byte rpi_to_esp_t
    # command packet (both zero-padded to 64 bytes).
    ESP32_SPI_BUS: Final[int] = _env_int("ESP32_SPI_BUS", 0)
    ESP32_SPI_DEVICE: Final[int] = _env_int("ESP32_SPI_DEVICE", 0)
    ESP32_SPI_SPEED_HZ: Final[int] = _env_int("ESP32_SPI_SPEED_HZ", 1_000_000)
    ESP32_SPI_MODE: Final[int] = _env_int("ESP32_SPI_MODE", 0)
    # GPIO (BCM) wired to the ESP32 IRQ line; LOW = fresh telemetry ready.
    ESP32_IRQ_PIN: Final[int] = _env_int("ESP32_IRQ_PIN", 23)
    # A telemetry frame older than this is treated as stale (read unhealthy).
    ESP32_FRAME_TIMEOUT_S: Final[float] = _env_float("ESP32_FRAME_TIMEOUT_S", 1.0)
    # Synthetic-detection distances used when the firmware reports a
    # drop / overhead flag (the firmware owns the threshold logic, not us).
    ESP32_DROP_DETECTION_M: Final[float] = _env_float("ESP32_DROP_DETECTION_M", 0.25)
    ESP32_OVERHEAD_DETECTION_M: Final[float] = _env_float("ESP32_OVERHEAD_DETECTION_M", 0.5)

    # UART bridge — used only by BatterySensor today (battery isn't in the
    # SPI packet yet). When the bridge port is missing, BatterySensor falls
    # back to a simulated drain so the rest of the system still boots.
    ESP32_PORT: Final[str] = _env_str("ESP32_PORT", "/dev/serial0")
    ESP32_BAUDRATE: Final[int] = _env_int("ESP32_BAUDRATE", 115200)

    HAPTICS_PIN: Final[int] = _env_int("HAPTICS_PIN", 26)
    BUZZER_PIN: Final[int] = _env_int("BUZZER_PIN", 27)

    ALERT_COOLDOWN_S: Final[float] = _env_float("ALERT_COOLDOWN_S", 3.0)
    ELECTRICAL_LOG_INTERVAL_S: Final[int] = _env_int("ELECTRICAL_LOG_INTERVAL_S", 30)

    TTS_ENABLED: Final[bool] = _env_bool("TTS_ENABLED", True)
    TTS_RATE_WPM: Final[int] = _env_int("TTS_RATE_WPM", 80)
    TTS_VOLUME: Final[float] = _env_float("TTS_VOLUME", 1.0)

    @classmethod
    def is_dev(cls) -> bool:
        return cls.ENVIRONMENT == Environment.DEV

    @classmethod
    def is_prod(cls) -> bool:
        return cls.ENVIRONMENT == Environment.PROD

    @classmethod
    def ensure_directories(cls) -> None:
        """Create required directories if they don't exist."""
        cls.DATA_DIR.mkdir(parents=True, exist_ok=True)
        cls.DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
