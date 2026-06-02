"""Dependency injection container.

`build_container()` is invoked once at startup and the resulting container
is attached to the FastAPI app. Route handlers reach in via the
`get_container()` helper. This is the only file in the api layer that
knows about concrete service / sensor classes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.config import Config
from detection.alert_engine import AlertEngine
from detection.detector import DetectionLoop
from detection.frame_buffer import FrameBuffer
from detection.yolo_model import YoloDetector
from output import BuzzerController, HapticsController, OutputQueue, SpeakerController
from sensors import (
    CameraSensor,
    Esp32SpiLink,
    StickTelemetrySensor,
)
from services import (
    DetectionService,
    ElectricalLoggerService,
    LocationService,
    MessageService,
    MetricsService,
    MovementAnalyzer,
    OutputService,
    SessionService,
    SosService,
)
from storage import (
    AlertRepository,
    CommandRepository,
    Database,
    DetectionRepository,
    ElectricalRepository,
    LocationRepository,
    MessageRepository,
    SessionRepository,
)
from storage.migrations import run_migrations
from utils.logger import get_logger


@dataclass
class Container:
    """Holds every long-lived object the API needs."""

    database: Database
    output_queue: OutputQueue
    spi_link: Esp32SpiLink
    detection_service: DetectionService
    location_service: LocationService
    output_service: OutputService
    message_service: MessageService
    session_service: SessionService
    electrical_logger: ElectricalLoggerService
    sos_service: SosService
    metrics_service: MetricsService
    movement_analyzer: MovementAnalyzer
    frame_buffer: FrameBuffer

    def start_all(self) -> None:
        log = get_logger("api.container")
        self.output_queue.start()
        self.location_service.start()
        self.detection_service.start()
        self.electrical_logger.start()
        self.sos_service.start()
        self.metrics_service.start()
        log.info("background services started")

    def stop_all(self) -> None:
        log = get_logger("api.container")
        self.metrics_service.stop()
        self.sos_service.stop()
        self.electrical_logger.stop()
        self.detection_service.stop()
        self.location_service.stop()
        self.output_service.stop()
        self.output_queue.stop()
        self.spi_link.close()
        self.database.close()
        log.info("background services stopped")


def build_container() -> Container:
    """Wire up every dependency. Called once during app startup."""
    Config.ensure_directories()

    database = Database()
    run_migrations(database)

    detection_repo = DetectionRepository(database)
    location_repo = LocationRepository(database)
    command_repo = CommandRepository(database)
    message_repo = MessageRepository(database)
    alert_repo = AlertRepository(database)
    session_repo = SessionRepository(database)
    electrical_repo = ElectricalRepository(database)

    # SPI link to the ESP32 sensor hub — shared by the telemetry sensor
    # (reads) and the haptics / buzzer controllers (command overrides).
    spi_link = Esp32SpiLink()

    haptics = HapticsController(link=spi_link)
    buzzer = BuzzerController(link=spi_link)
    speaker = SpeakerController()
    output_queue = OutputQueue()

    # Central place for the demo latency metrics. Logs each one as a
    # structured INFO line and keeps a rolling history for /api/metrics.
    # The LSTM sequence-data heartbeat (configured further down, once
    # location_service exists) shows how much trajectory input the future
    # TrajectoryService would have available right now.
    metrics_service = MetricsService()

    output_service = OutputService(
        haptics=haptics,
        buzzer=buzzer,
        speaker=speaker,
        queue=output_queue,
        command_repo=command_repo,
        message_repo=message_repo,
        link=spi_link,
    )
    message_service = MessageService(output=output_service, repository=message_repo)
    session_service = SessionService(repository=session_repo)

    # The ESP32 is the sensor hub: it owns the LiDAR, both ultrasonic
    # sensors and the GPS, and returns a telemetry packet on every SPI
    # transfer. One telemetry sensor feeds both detection and location.
    telemetry = StickTelemetrySensor(link=spi_link)

    camera = CameraSensor()
    yolo = YoloDetector()
    frame_buffer = FrameBuffer()
    detection_loop = DetectionLoop(
        camera=camera,
        yolo=yolo,
        telemetry=telemetry,
        frame_buffer=frame_buffer,
    )
    detection_service = DetectionService(
        loop=detection_loop,
        alert_engine=AlertEngine(),
        output=output_service,
        detection_repo=detection_repo,
        alert_repo=alert_repo,
        metrics=metrics_service,
    )

    location_service = LocationService(telemetry=telemetry, repository=location_repo)

    electrical_logger = ElectricalLoggerService(
        repository=electrical_repo,
        fps_callback=detection_service.fps,
        inference_ms_callback=detection_service.inference_time_ms,
    )

    sos_service = SosService(
        telemetry=telemetry,
        location_getter=location_service.latest,
        metrics=metrics_service,
    )
    # Let OutputService suppress detection haptics+buzzer while the SOS
    # button is held; earpiece TTS keeps flowing for guardian messages.
    output_service.set_sos_active_getter(sos_service.is_active)

    # LSTM movement analyzer. Subscribes to the detection callback fan-out
    # (so it doesn't displace DetectionService's own dispatch) and emits
    # navigational narration via SpeechPriority.LSTM. Each narration also
    # lands in the telemetry CSV via MetricsService.
    movement_analyzer = MovementAnalyzer(output=output_service, metrics=metrics_service)
    detection_service.add_listener(movement_analyzer.on_detections)

    # Late-bind the LSTM heartbeat data source. Reports how much
    # trajectory input the MovementAnalyzer has available right now.
    def _trajectory_snapshot() -> dict[str, Any]:
        from utils.converters import unix_timestamp

        since = unix_timestamp() - 3600
        recent = location_repo.since(since)
        return {
            "window_size": len(recent),
            "distance_today_km": round(location_service.distance_today_km(), 3),
        }

    metrics_service.set_trajectory_snapshot(_trajectory_snapshot)

    return Container(
        database=database,
        output_queue=output_queue,
        spi_link=spi_link,
        detection_service=detection_service,
        location_service=location_service,
        output_service=output_service,
        message_service=message_service,
        session_service=session_service,
        electrical_logger=electrical_logger,
        sos_service=sos_service,
        metrics_service=metrics_service,
        movement_analyzer=movement_analyzer,
        frame_buffer=frame_buffer,
    )


_container: Container | None = None


def set_container(container: Container) -> None:
    global _container
    _container = container


def get_container() -> Container:
    if _container is None:
        raise RuntimeError("container not initialized")
    return _container
