"""Tests for the sensors layer."""

from __future__ import annotations

from typing import Any

from core.exceptions import SensorError
from sensors.base import SensorBase
from sensors.esp32_spi import build_command, parse_telemetry
from sensors.gps import parse_gpgga


class _FakeSensor(SensorBase):
    name = "fake"

    def __init__(self, payload: dict[str, Any] | None = None, fail: bool = False) -> None:
        super().__init__()
        self._payload = payload or {"value": 1}
        self._fail = fail

    def _read_impl(self) -> dict[str, Any]:
        if self._fail:
            raise SensorError("simulated failure")
        return dict(self._payload)


class TestSensorBase:
    def test_successful_read(self) -> None:
        sensor = _FakeSensor(payload={"x": 42})
        reading = sensor.read()
        assert reading.healthy
        assert reading.data == {"x": 42}
        assert sensor.is_healthy()

    def test_failed_read_returns_unhealthy(self) -> None:
        sensor = _FakeSensor(fail=True)
        reading = sensor.read()
        assert not reading.healthy
        assert reading.error
        assert not sensor.is_healthy()
        assert sensor.status().consecutive_failures == 1

    def test_recovers_after_failure(self) -> None:
        sensor = _FakeSensor(fail=True)
        sensor.read()
        sensor._fail = False
        reading = sensor.read()
        assert reading.healthy
        assert sensor.status().consecutive_failures == 0


class TestGpsParsing:
    def test_parse_valid_gpgga(self) -> None:
        sentence = "$GPGGA,123519,1435.97,N,12059.05,E,1,08,0.9,545.4,M,46.9,M,,*47"
        result = parse_gpgga(sentence)
        assert result is not None
        assert 14.0 < result["latitude"] < 15.0
        assert 120.0 < result["longitude"] < 121.0

    def test_parse_no_fix_returns_none(self) -> None:
        sentence = "$GPGGA,123519,,,,,0,00,,,M,,M,,*48"
        assert parse_gpgga(sentence) is None

    def test_parse_non_gpgga_returns_none(self) -> None:
        assert parse_gpgga("$GPRMC,123519,A,1435.97,N,12059.05,E,*47") is None


def _telemetry_frame(
    lat: float = 0.0,
    lng: float = 0.0,
    lidar_cm: int = -1,
    sos: int = 0,
    drop: int = 0,
    overhead: int = 0,
    gps_valid: int = 0,
    seq: int = 0,
) -> bytes:
    """Build a 64-byte SPI frame matching the firmware's esp_to_rpi_t."""
    import struct

    packet = struct.pack("<ffhBBBBB", lat, lng, lidar_cm, sos, drop, overhead, gps_valid, seq)
    return packet + bytes(64 - len(packet))


class TestEspSpiTelemetry:
    def test_parse_valid_frame(self) -> None:
        frame = _telemetry_frame(
            lat=14.5995, lng=120.9842, lidar_cm=85, drop=1, gps_valid=1, seq=42
        )
        result = parse_telemetry(frame)
        assert result is not None
        assert round(result["latitude"], 4) == 14.5995
        assert round(result["longitude"], 4) == 120.9842
        assert result["lidar_distance_m"] == 0.85
        assert result["sos_active"] is False
        assert result["drop_detected"] is True
        assert result["overhead_detected"] is False
        assert result["gps_valid"] is True
        assert result["seq"] == 42

    def test_lidar_negative_means_no_reading(self) -> None:
        # lidar_cm = -1 packs as 0xFFFF, so this is a valid (non-empty)
        # frame reporting "no LiDAR reading".
        result = parse_telemetry(_telemetry_frame(lidar_cm=-1, seq=3))
        assert result is not None
        assert result["lidar_distance_m"] is None

    def test_all_zero_frame_returns_none(self) -> None:
        # A literally all-zero packet (lidar_cm=0, every field 0) means the
        # ESP32 has not loaded telemetry yet.
        assert parse_telemetry(_telemetry_frame(lidar_cm=0)) is None

    def test_short_frame_returns_none(self) -> None:
        assert parse_telemetry(b"\x01\x02\x03") is None

    def test_build_command_is_64_bytes(self) -> None:
        cmd = build_command(buzzer_cmd=3, vibrator_cmd=1)
        assert len(cmd) == 64
        assert cmd[0] == 3
        assert cmd[1] == 1
        assert cmd[2] == 0 and cmd[3] == 0

    def test_build_command_default_is_all_zero(self) -> None:
        # The all-zero frame is the firmware-ignored "no override" command.
        assert build_command() == bytes(64)
