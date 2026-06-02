"""Tests for the services layer (orchestration)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from services.message_service import MessageService
from services.session_service import SessionService
from storage import (
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
