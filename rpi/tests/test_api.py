"""Smoke tests for the FastAPI app — endpoints reachable, schemas honoured."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

try:
    from fastapi.testclient import TestClient

    _FASTAPI_AVAILABLE = True
except ImportError:  # pragma: no cover
    TestClient = None  # type: ignore[assignment]
    _FASTAPI_AVAILABLE = False


pytestmark = pytest.mark.skipif(not _FASTAPI_AVAILABLE, reason="fastapi/httpx not installed")


def _build_test_container(database):
    """Construct a Container with mocked sensors and a real database."""
    from api.dependencies import Container
    from output import (
        BuzzerController,
        HapticsController,
        OutputQueue,
        SpeakerController,
    )
    from services import (
        MessageService,
        OutputService,
        SessionService,
    )
    from storage import (
        CommandRepository,
        MessageRepository,
        SessionRepository,
    )

    bridge = MagicMock()
    bridge.is_healthy.return_value = True
    bridge.send_vibration.return_value = True
    bridge.send_buzz.return_value = True

    haptics = HapticsController(bridge=bridge)
    buzzer = BuzzerController(bridge=bridge)
    speaker = SpeakerController()
    queue = OutputQueue()
    queue.start()

    command_repo = CommandRepository(database)
    message_repo = MessageRepository(database)

    output_service = OutputService(
        haptics=haptics,
        buzzer=buzzer,
        speaker=speaker,
        queue=queue,
        command_repo=command_repo,
        message_repo=message_repo,
    )

    # Mock the heavy bits so startup hooks don't try to open hardware.
    detection_service = MagicMock()
    detection_service.latest_detections.return_value = []
    detection_service.latest_alert.return_value = None
    detection_service.fps.return_value = 5.5
    detection_service.inference_time_ms.return_value = 120

    location_service = MagicMock()
    location_service.latest.return_value = {
        "latitude": 14.6,
        "longitude": 120.98,
        "altitude": 10.0,
        "accuracy_m": 5.0,
        "timestamp": "2024-05-06T12:00:23Z",
    }

    battery_service = MagicMock()
    battery_service.latest.return_value = {
        "voltage_v": 4.0,
        "current_ma": 2000,
        "percentage": 80,
        "temperature_c": 35.0,
        "health": "good",
        "estimated_runtime_minutes": 180,
    }

    session_service = SessionService(repository=SessionRepository(database))
    message_service = MessageService(output=output_service, repository=message_repo)
    electrical_logger = MagicMock()

    return Container(
        database=database,
        output_queue=queue,
        bridge=bridge,
        detection_service=detection_service,
        location_service=location_service,
        battery_service=battery_service,
        output_service=output_service,
        message_service=message_service,
        session_service=session_service,
        electrical_logger=electrical_logger,
    )


@pytest.fixture
def client(database):
    from api.app import create_app
    from api.dependencies import set_container

    container = _build_test_container(database)
    set_container(container)
    app = create_app(container=container)
    with TestClient(app) as c:
        yield c
    container.output_queue.stop()


class TestApi:
    def test_health(self, client) -> None:
        resp = client.get("/api/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_battery(self, client) -> None:
        resp = client.get("/api/battery")
        assert resp.status_code == 200
        body = resp.json()
        assert body["percentage"] == 80
        assert body["health"] == "good"

    def test_location(self, client) -> None:
        resp = client.get("/api/location")
        assert resp.status_code == 200
        assert resp.json()["latitude"] == 14.6

    def test_vibrate(self, client) -> None:
        resp = client.post("/api/vibrate", json={"intensity": 200, "duration_ms": 250})
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    def test_buzz(self, client) -> None:
        resp = client.post("/api/buzz", json={"frequency_hz": 2500, "duration_ms": 500})
        assert resp.status_code == 200

    def test_message_rejects_empty(self, client) -> None:
        resp = client.post("/api/message", json={"text": "", "priority": "normal"})
        assert resp.status_code == 422

    def test_message_send(self, client) -> None:
        resp = client.post("/api/message", json={"text": "Slow down", "priority": "high"})
        assert resp.status_code == 200

    def test_emergency_sos(self, client) -> None:
        resp = client.post("/api/emergency/sos")
        assert resp.status_code == 200

    def test_vibrate_validates_intensity(self, client) -> None:
        resp = client.post("/api/vibrate", json={"intensity": 999, "duration_ms": 100})
        assert resp.status_code == 422

    def test_buzz_validates_frequency(self, client) -> None:
        resp = client.post("/api/buzz", json={"frequency_hz": 50, "duration_ms": 100})
        assert resp.status_code == 422
