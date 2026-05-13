"""Tests for the services layer (orchestration)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from services.battery_service import BatteryService
from services.message_service import MessageService
from services.session_service import SessionService
from storage import (
    BatteryRepository,
    MessageRepository,
    SessionRepository,
)


class TestSessionService:
    def test_start_creates_session(self, database) -> None:
        repo = SessionRepository(database)
        service = SessionService(repository=repo)
        session_id = service.start()
        assert session_id
        assert session_id.startswith("session_")
        snapshot = service.snapshot()
        assert snapshot["session_id"] == session_id
        assert snapshot["detection_count"] == 0

    def test_increment_counters(self, database) -> None:
        service = SessionService(repository=SessionRepository(database))
        service.start()
        service.increment_detections(3)
        service.increment_alerts(2)
        service.add_distance_km(1.25)
        snap = service.snapshot()
        assert snap["detection_count"] == 3
        assert snap["alert_count"] == 2
        assert snap["distance_km"] == 1.25

    def test_end_returns_summary(self, database) -> None:
        service = SessionService(repository=SessionRepository(database))
        service.start()
        service.increment_detections(5)
        summary = service.end()
        assert summary is not None
        assert summary["detection_count"] == 5


class TestBatteryService:
    def test_warnings_fire_at_each_threshold(self, database) -> None:
        sensor = MagicMock()
        sensor.initialize.return_value = None
        sensor.read.side_effect = self._make_readings([45, 24, 8])

        warnings: list[tuple[str, object]] = []

        def on_warning(message: str, tone) -> None:
            warnings.append((message, tone))

        service = BatteryService(
            sensor=sensor,
            repository=BatteryRepository(database),
            on_warning=on_warning,
            interval_s=0,
        )
        # Call internal tick directly to avoid spinning up threads.
        service._tick()
        service._tick()
        service._tick()

        triggered_levels = [w[0] for w in warnings]
        assert any("50" in m for m in triggered_levels)
        assert any("25" in m for m in triggered_levels)
        assert any("10" in m for m in triggered_levels)

    def test_warning_fires_only_once_per_threshold(self, database) -> None:
        sensor = MagicMock()
        sensor.read.side_effect = self._make_readings([45, 44, 43])
        warnings: list = []
        service = BatteryService(
            sensor=sensor,
            repository=BatteryRepository(database),
            on_warning=lambda m, t: warnings.append(m),
            interval_s=0,
        )
        service._tick()
        service._tick()
        service._tick()
        # Only one "50%" warning even though three readings crossed the threshold.
        fifty_warnings = [w for w in warnings if "50" in w]
        assert len(fifty_warnings) == 1

    @staticmethod
    def _make_readings(percentages: list[int]) -> list[MagicMock]:
        readings = []
        for pct in percentages:
            r = MagicMock()
            r.healthy = True
            r.data = {
                "voltage_v": 3.5 + pct / 100.0 * 0.7,
                "current_ma": 2000,
                "percentage": pct,
                "temperature_c": 35.0,
                "health": "warning" if pct < 80 else "good",
            }
            from utils.converters import now_utc

            r.timestamp = now_utc()
            readings.append(r)
        return readings


class TestMessageService:
    def test_empty_message_raises(self, database) -> None:
        output = MagicMock()
        output.speak.return_value = "msg_x"
        service = MessageService(output=output, repository=MessageRepository(database))
        with pytest.raises(ValueError):
            service.send("   ")

    def test_long_message_is_truncated(self, database) -> None:
        output = MagicMock()
        output.speak.return_value = "msg_x"
        service = MessageService(output=output, repository=MessageRepository(database))
        result = service.send("x" * 1000)
        assert len(result["text"]) == 500

    def test_send_delegates_to_output(self, database) -> None:
        output = MagicMock()
        output.speak.return_value = "msg_x"
        service = MessageService(output=output, repository=MessageRepository(database))
        result = service.send("hello", priority="high")
        output.speak.assert_called_once_with("hello", priority="high")
        assert result["message_id"] == "msg_x"
