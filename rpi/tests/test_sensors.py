"""Tests for the sensors layer."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from core.exceptions import SensorError
from core.types import HealthStatus
from sensors.base import SensorBase
from sensors.battery import (
    BatterySensor,
    classify_health,
    voltage_to_percentage,
)
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


class TestBatteryHelpers:
    def test_voltage_to_percentage_clamps(self) -> None:
        assert voltage_to_percentage(3.0) == 0
        assert voltage_to_percentage(4.3) == 100

    def test_voltage_to_percentage_linear(self) -> None:
        # Midpoint of [3.3, 4.2] ≈ 3.75 -> ~50%.
        pct = voltage_to_percentage(3.75)
        assert 45 <= pct <= 55

    def test_classify_health_levels(self) -> None:
        assert classify_health(90, 4.8, 30.0) == HealthStatus.GOOD
        assert classify_health(50, 4.0, 30.0) == HealthStatus.WARNING
        assert classify_health(10, 3.4, 30.0) == HealthStatus.CRITICAL
        assert classify_health(90, 4.8, 60.0) == HealthStatus.CRITICAL


class TestBatterySensor:
    def test_uses_bridge_when_available(self) -> None:
        bridge = MagicMock()
        bridge.is_healthy.return_value = True
        bridge.request_battery_status.return_value = {
            "voltage_v": 4.0,
            "current_ma": 1500,
            "percentage": 70,
            "temperature_c": 30.0,
        }
        sensor = BatterySensor(bridge=bridge)
        reading = sensor.read()
        assert reading.healthy
        assert reading.data["percentage"] == 70
        bridge.request_battery_status.assert_called_once()

    def test_falls_back_to_fake_payload_when_no_bridge(self) -> None:
        sensor = BatterySensor(bridge=None)
        reading = sensor.read()
        assert reading.healthy
        assert "voltage_v" in reading.data
        assert "percentage" in reading.data


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
