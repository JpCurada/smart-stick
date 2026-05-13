"""GPS sensor reading NMEA sentences over UART."""

from __future__ import annotations

from typing import Any

from core.config import Config
from sensors.base import SensorBase

try:
    import serial  # type: ignore[import-not-found]

    _SERIAL_AVAILABLE = True
except Exception:  # pragma: no cover
    serial = None  # type: ignore[assignment]
    _SERIAL_AVAILABLE = False


def _parse_lat_lon(raw: str, hemisphere: str) -> float | None:
    """Convert NMEA ddmm.mmmm format to decimal degrees."""
    if not raw or not hemisphere:
        return None
    try:
        dot = raw.index(".")
    except ValueError:
        return None
    degrees = int(raw[: dot - 2])
    minutes = float(raw[dot - 2 :])
    decimal = degrees + minutes / 60.0
    if hemisphere in {"S", "W"}:
        decimal = -decimal
    return decimal


def parse_gpgga(sentence: str) -> dict[str, Any] | None:
    """Parse a $GPGGA sentence into a location dict."""
    if not sentence.startswith("$GPGGA"):
        return None
    parts = sentence.split(",")
    if len(parts) < 10:
        return None
    fix_quality = parts[6]
    if fix_quality == "0":
        return None
    latitude = _parse_lat_lon(parts[2], parts[3])
    longitude = _parse_lat_lon(parts[4], parts[5])
    if latitude is None or longitude is None:
        return None
    try:
        accuracy = float(parts[8]) if parts[8] else None
        altitude = float(parts[9]) if parts[9] else None
    except ValueError:
        accuracy, altitude = None, None
    return {
        "latitude": latitude,
        "longitude": longitude,
        "altitude": altitude,
        "accuracy_m": accuracy,
        "fix_quality": int(fix_quality) if fix_quality.isdigit() else 0,
    }


class GpsSensor(SensorBase):
    """Reads one GPS fix per `read()` call."""

    name = "gps"

    def __init__(
        self,
        port: str | None = None,
        baudrate: int | None = None,
        read_timeout_s: float = 1.0,
    ) -> None:
        super().__init__()
        self._port = port if port is not None else Config.GPS_PORT
        self._baudrate = baudrate if baudrate is not None else Config.GPS_BAUDRATE
        self._read_timeout_s = read_timeout_s
        self._serial: Any = None

    def _initialize_impl(self) -> None:
        if not _SERIAL_AVAILABLE:
            self._require(False, "pyserial is not installed")
        self._serial = serial.Serial(  # type: ignore[union-attr]
            self._port, self._baudrate, timeout=self._read_timeout_s
        )

    def _read_impl(self) -> dict[str, Any]:
        self._require(self._serial is not None, "gps not initialized")
        for _ in range(20):
            raw = self._serial.readline().decode("ascii", errors="ignore").strip()
            parsed = parse_gpgga(raw)
            if parsed is not None:
                return parsed
        self._require(False, "no valid NMEA fix in window")
        return {}

    def _close_impl(self) -> None:
        if self._serial is not None:
            self._serial.close()
            self._serial = None
