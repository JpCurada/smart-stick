"""Dependency injection container.

`build_container()` is invoked once at startup and the resulting container
is attached to the FastAPI app. Route handlers reach in via the
`get_container()` helper. This is the only file in the api layer that
knows about concrete service / sensor classes.
"""

from __future__ import annotations

from dataclasses import dataclass

from core.config import Config
from detection.alert_engine import AlertEngine
from detection.detector import DetectionLoop
from detection.frame_buffer import FrameBuffer
from detection.yolo_model import YoloDetector
from output import BuzzerController, HapticsController, OutputQueue, SpeakerController
from sensors import (
    BatterySensor,
    CameraSensor,
    Esp32Bridge,
    GpsSensor,
    LidarSensor,
    UltrasonicSensor,
)
from services import (
    BatteryService,
    DetectionService,
    ElectricalLoggerService,
    LocationService,
    MessageService,
    OutputService,
    SessionService,
)
from storage import (
    AlertRepository,
    BatteryRepository,
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
    bridge: Esp32Bridge
    detection_service: DetectionService
    location_service: LocationService
    battery_service: BatteryService
    output_service: OutputService
    message_service: MessageService
    session_service: SessionService
    electrical_logger: ElectricalLoggerService
    frame_buffer: FrameBuffer

    def start_all(self) -> None:
        log = get_logger("api.container")
        self.output_queue.start()
        self.location_service.start()
        self.battery_service.start()
        self.detection_service.start()
        self.electrical_logger.start()
        log.info("background services started")

    def stop_all(self) -> None:
        log = get_logger("api.container")
        self.electrical_logger.stop()
        self.detection_service.stop()
        self.battery_service.stop()
        self.location_service.stop()
        self.output_queue.stop()
        self.database.close()
        log.info("background services stopped")


def build_container() -> Container:
    """Wire up every dependency. Called once during app startup."""
    Config.ensure_directories()

    database = Database()
    run_migrations(database)

    detection_repo = DetectionRepository(database)
    location_repo = LocationRepository(database)
    battery_repo = BatteryRepository(database)
    command_repo = CommandRepository(database)
    message_repo = MessageRepository(database)
    alert_repo = AlertRepository(database)
    session_repo = SessionRepository(database)
    electrical_repo = ElectricalRepository(database)

    bridge = Esp32Bridge()
    haptics = HapticsController(bridge=bridge)
    buzzer = BuzzerController(bridge=bridge)
    speaker = SpeakerController()
    output_queue = OutputQueue()

    output_service = OutputService(
        haptics=haptics,
        buzzer=buzzer,
        speaker=speaker,
        queue=output_queue,
        command_repo=command_repo,
        message_repo=message_repo,
    )
    message_service = MessageService(output=output_service, repository=message_repo)
    session_service = SessionService(repository=session_repo)

    camera = CameraSensor()
    yolo = YoloDetector()
    lidar = LidarSensor()
    overhead = UltrasonicSensor(
        name="ultrasonic_overhead",
        trigger_pin=Config.ULTRASONIC_OVERHEAD_TRIG_PIN,
        echo_pin=Config.ULTRASONIC_OVERHEAD_ECHO_PIN,
    )
    down = UltrasonicSensor(
        name="ultrasonic_down",
        trigger_pin=Config.ULTRASONIC_DOWN_TRIG_PIN,
        echo_pin=Config.ULTRASONIC_DOWN_ECHO_PIN,
    )
    frame_buffer = FrameBuffer()
    detection_loop = DetectionLoop(
        camera=camera,
        yolo=yolo,
        lidar=lidar,
        overhead_ultrasonic=overhead,
        down_ultrasonic=down,
        frame_buffer=frame_buffer,
    )
    detection_service = DetectionService(
        loop=detection_loop,
        alert_engine=AlertEngine(),
        output=output_service,
        detection_repo=detection_repo,
        alert_repo=alert_repo,
    )

    gps = GpsSensor()
    location_service = LocationService(gps=gps, repository=location_repo)

    battery_sensor = BatterySensor(bridge=bridge)

    def on_battery_warning(message: str, tone) -> None:
        output_service.play_tone(tone)
        output_service.speak(message, priority="high")

    battery_service = BatteryService(
        sensor=battery_sensor,
        repository=battery_repo,
        on_warning=on_battery_warning,
    )

    electrical_logger = ElectricalLoggerService(
        repository=electrical_repo,
        battery_snapshot=battery_service.latest,
        fps_callback=detection_service.fps,
        inference_ms_callback=detection_service.inference_time_ms,
    )

    return Container(
        database=database,
        output_queue=output_queue,
        bridge=bridge,
        detection_service=detection_service,
        location_service=location_service,
        battery_service=battery_service,
        output_service=output_service,
        message_service=message_service,
        session_service=session_service,
        electrical_logger=electrical_logger,
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
