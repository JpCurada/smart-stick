"""Build a fully-wired Container using fake sensors.

Imported by mock/run.py. All real hardware classes are replaced with their
fake counterparts; everything else (database, services, API layer) is real.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Put rpi/ on the path so all existing imports resolve.
_RPI = Path(__file__).resolve().parent.parent / "rpi"
if str(_RPI) not in sys.path:
    sys.path.insert(0, str(_RPI))

from mock.fake_sensors import (  # noqa: E402
    FakeBattery,
    FakeCamera,
    FakeEsp32Bridge,
    FakeGps,
    FakeLidar,
    FakeSpeaker,
    FakeUltrasonic,
    FakeYoloDetector,
)

from api.dependencies import Container  # noqa: E402
from core.config import Config  # noqa: E402
from detection.alert_engine import AlertEngine  # noqa: E402
from detection.detector import DetectionLoop  # noqa: E402
from output import BuzzerController, HapticsController, OutputQueue  # noqa: E402
from sensors.battery import BatterySensor  # noqa: E402
from services import (  # noqa: E402
    BatteryService,
    DetectionService,
    ElectricalLoggerService,
    LocationService,
    MessageService,
    OutputService,
    SessionService,
)
from storage import (  # noqa: E402
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
from storage.migrations import run_migrations  # noqa: E402
from utils.logger import get_logger  # noqa: E402


def build_mock_container() -> Container:
    log = get_logger("mock.container")
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

    bridge = FakeEsp32Bridge()
    haptics = HapticsController(bridge=bridge)   # type: ignore[arg-type]
    buzzer = BuzzerController(bridge=bridge)     # type: ignore[arg-type]
    speaker = FakeSpeaker()                      # type: ignore[assignment]
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

    fake_camera = FakeCamera()
    fake_yolo = FakeYoloDetector()
    fake_lidar = FakeLidar()
    fake_overhead = FakeUltrasonic("ultrasonic_overhead")
    fake_down = FakeUltrasonic("ultrasonic_down")

    detection_loop = DetectionLoop(
        camera=fake_camera,      # type: ignore[arg-type]
        yolo=fake_yolo,          # type: ignore[arg-type]
        lidar=fake_lidar,        # type: ignore[arg-type]
        overhead_ultrasonic=fake_overhead,  # type: ignore[arg-type]
        down_ultrasonic=fake_down,          # type: ignore[arg-type]
    )
    detection_service = DetectionService(
        loop=detection_loop,
        alert_engine=AlertEngine(),
        output=output_service,
        detection_repo=detection_repo,
        alert_repo=alert_repo,
    )

    fake_gps = FakeGps()
    location_service = LocationService(gps=fake_gps, repository=location_repo)  # type: ignore[arg-type]

    fake_battery_sensor = FakeBattery()

    def on_battery_warning(message: str, tone) -> None:
        output_service.play_tone(tone)
        output_service.speak(message, priority="high")

    battery_service = BatteryService(
        sensor=fake_battery_sensor,  # type: ignore[arg-type]
        repository=battery_repo,
        on_warning=on_battery_warning,
    )

    electrical_logger = ElectricalLoggerService(
        repository=electrical_repo,
        battery_snapshot=battery_service.latest,
        fps_callback=detection_service.fps,
        inference_ms_callback=detection_service.inference_time_ms,
    )

    log.info("mock container wired — all sensors are fake")
    return Container(
        database=database,
        output_queue=output_queue,
        bridge=bridge,           # type: ignore[arg-type]
        detection_service=detection_service,
        location_service=location_service,
        battery_service=battery_service,
        output_service=output_service,
        message_service=message_service,
        session_service=session_service,
        electrical_logger=electrical_logger,
    )
