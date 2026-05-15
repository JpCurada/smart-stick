"""Detection loop orchestration.

Reads camera frames, asks the YOLO model for predictions, fuses distance
information from LIDAR / ultrasonic, and emits high-level Detection
objects through a callback. The detector deliberately knows nothing about
storage, output, or the API — those concerns live in services.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable

from core.config import Config
from core.types import Detection, ObjectClass
from detection.distance_fusion import fuse_distance
from detection.frame_buffer import FrameBuffer
from detection.yolo_model import YoloDetector, YoloPrediction
from sensors import CameraSensor, LidarSensor, UltrasonicSensor
from utils.converters import now_utc
from utils.logger import get_logger

DetectionCallback = Callable[[list[Detection], dict[str, object]], None]


class DetectionLoop:
    """Threaded detection pipeline. Start once, stop on shutdown."""

    def __init__(
        self,
        camera: CameraSensor,
        yolo: YoloDetector,
        lidar: LidarSensor | None = None,
        overhead_ultrasonic: UltrasonicSensor | None = None,
        down_ultrasonic: UltrasonicSensor | None = None,
        on_detections: DetectionCallback | None = None,
        fps: int | None = None,
        frame_buffer: FrameBuffer | None = None,
    ) -> None:
        self._camera = camera
        self._yolo = yolo
        self._lidar = lidar
        self._overhead = overhead_ultrasonic
        self._down = down_ultrasonic
        self._on_detections = on_detections
        self._fps = fps if fps is not None else Config.DETECTION_FPS
        self._period_s = 1.0 / max(1, self._fps)
        self._stop_flag = threading.Event()
        self._thread: threading.Thread | None = None
        self._log = get_logger("detection.loop")
        self._last_inference_ms = 0
        self._frames_processed = 0
        self._start_time = 0.0
        self._frame_buffer = frame_buffer

    def set_callback(self, callback: DetectionCallback) -> None:
        """Register the listener invoked once per processed frame."""
        self._on_detections = callback

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._camera.initialize()
        self._yolo.load()
        if self._lidar is not None:
            self._lidar.initialize()
        if self._overhead is not None:
            self._overhead.initialize()
        if self._down is not None:
            self._down.initialize()

        self._stop_flag.clear()
        self._start_time = time.monotonic()
        self._thread = threading.Thread(target=self._run, name="detection-loop", daemon=True)
        self._thread.start()
        self._log.info("detection loop started at %d fps", self._fps)

    def stop(self, timeout_s: float = 3.0) -> None:
        self._stop_flag.set()
        if self._thread is not None:
            self._thread.join(timeout=timeout_s)
            self._thread = None

    def fps(self) -> float:
        elapsed = max(1e-6, time.monotonic() - self._start_time)
        return self._frames_processed / elapsed

    def last_inference_ms(self) -> int:
        return self._last_inference_ms

    def _run(self) -> None:
        while not self._stop_flag.is_set():
            loop_start = time.monotonic()
            try:
                self._process_one_frame()
            except Exception as exc:
                self._log.warning("frame processing error: %s", exc)
            self._sleep_for_target_fps(loop_start)

    def _process_one_frame(self) -> None:
        reading = self._camera.read()
        if not reading.healthy or "frame" not in reading.data:
            return

        frame = reading.data["frame"]
        if self._frame_buffer is not None:
            self._frame_buffer.update(frame, time.time())

        inference_start = time.monotonic()
        predictions = self._yolo.predict(frame)
        self._last_inference_ms = int((time.monotonic() - inference_start) * 1000)
        self._frames_processed += 1

        lidar_distance = self._read_lidar_distance()
        detections = [self._build_detection(p, lidar_distance) for p in predictions]

        if self._overhead is not None:
            overhead_distance = self._read_ultrasonic_distance(self._overhead)
            if overhead_distance is not None and overhead_distance < 0.5:
                detections.append(
                    self._synthetic_detection(ObjectClass.OVERHEAD, overhead_distance)
                )

        if self._down is not None:
            down_distance = self._read_ultrasonic_distance(self._down)
            if down_distance is not None and down_distance < 0.3:
                detections.append(self._synthetic_detection(ObjectClass.STAIRS, down_distance))

        if self._on_detections is not None:
            meta = {
                "inference_ms": self._last_inference_ms,
                "frame_width": reading.data.get("width"),
                "frame_height": reading.data.get("height"),
            }
            self._on_detections(detections, meta)

    def _build_detection(
        self,
        prediction: YoloPrediction,
        lidar_distance_m: float | None,
    ) -> Detection:
        fused = fuse_distance(
            camera_distance_m=prediction.distance_estimate_m,
            lidar_distance_m=lidar_distance_m,
        )
        return Detection(
            object_class=prediction.object_class,
            confidence=prediction.confidence,
            distance_m=fused if fused is not None else 99.0,
            bbox=prediction.bbox,
        )

    def _read_lidar_distance(self) -> float | None:
        if self._lidar is None:
            return None
        reading = self._lidar.read()
        if not reading.healthy:
            return None
        return reading.data.get("distance_m")

    def _read_ultrasonic_distance(self, sensor: UltrasonicSensor) -> float | None:
        reading = sensor.read()
        if not reading.healthy:
            return None
        return reading.data.get("distance_m")

    def _synthetic_detection(self, object_class: ObjectClass, distance_m: float) -> Detection:
        return Detection(
            object_class=object_class,
            confidence=1.0,
            distance_m=distance_m,
            bbox=None,
            timestamp=now_utc(),
        )

    def _sleep_for_target_fps(self, loop_start: float) -> None:
        elapsed = time.monotonic() - loop_start
        sleep_s = self._period_s - elapsed
        if sleep_s > 0:
            time.sleep(sleep_s)
