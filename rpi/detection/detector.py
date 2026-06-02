"""Detection loop orchestration.

Reads camera frames, asks the YOLO model for predictions, fuses distance
information from the ESP32 telemetry stream (LiDAR), and emits high-level
Detection objects through a callback. Drop (stairs/curb) and overhead
obstacle detections come straight from the firmware's confirmed flags —
the ESP32 owns that decision logic. The detector deliberately knows
nothing about storage, output, or the API — those concerns live in
services.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable

from core.config import Config
from core.types import Detection, ObjectClass
from detection.distance_fusion import fuse_distance_with_source
from detection.frame_buffer import FrameBuffer
from detection.yolo_model import YoloDetector, YoloPrediction
from sensors import CameraSensor, StickTelemetrySensor
from utils.converters import now_utc
from utils.logger import get_logger

DetectionCallback = Callable[[list[Detection], dict[str, object]], None]


class DetectionLoop:
    """Threaded detection pipeline. Start once, stop on shutdown."""

    def __init__(
        self,
        camera: CameraSensor,
        yolo: YoloDetector,
        telemetry: StickTelemetrySensor | None = None,
        on_detections: DetectionCallback | None = None,
        fps: int | None = None,
        frame_buffer: FrameBuffer | None = None,
    ) -> None:
        self._camera = camera
        self._yolo = yolo
        self._telemetry = telemetry
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
        if self._telemetry is not None:
            self._telemetry.initialize()

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

        inference_start = time.monotonic()
        predictions = self._yolo.predict(frame)
        self._last_inference_ms = int((time.monotonic() - inference_start) * 1000)
        self._frames_processed += 1

        # Marker for "obstacle detection" latency: anything synthesized from a
        # firmware-confirmed flag (drop / overhead) is measured from here.
        telemetry_read_at = time.monotonic()
        telemetry = self._read_telemetry()
        lidar_distance = telemetry.get("lidar_distance_m") if telemetry else None
        detections = [self._build_detection(p, lidar_distance) for p in predictions]

        # Drop / overhead are firmware-confirmed flags — trust them directly
        # instead of re-thresholding raw distances on the RPi.
        firmware_flag_sources: list[str] = []
        if telemetry is not None:
            if telemetry.get("overhead_detected"):
                detections.append(
                    self._synthetic_detection(
                        ObjectClass.OVERHEAD, Config.ESP32_OVERHEAD_DETECTION_M
                    )
                )
                firmware_flag_sources.append("overhead")
            if telemetry.get("drop_detected"):
                detections.append(
                    self._synthetic_detection(ObjectClass.STAIRS, Config.ESP32_DROP_DETECTION_M)
                )
                firmware_flag_sources.append("drop")

        if self._frame_buffer is not None:
            annotated = self._annotate_frame(frame, predictions, detections)
            self._frame_buffer.update(annotated, time.time())

        if self._on_detections is not None:
            meta = {
                "inference_ms": self._last_inference_ms,
                "frame_width": reading.data.get("width"),
                "frame_height": reading.data.get("height"),
                "telemetry_read_at": telemetry_read_at,
                "firmware_flag_sources": firmware_flag_sources,
            }
            self._on_detections(detections, meta)

    def _annotate_frame(
        self,
        frame: object,
        predictions: list[YoloPrediction],
        detections: list[Detection],
    ) -> object:
        try:
            import cv2  # type: ignore[import-not-found]
        except Exception:
            return frame

        # Pair YOLO predictions with their fused-distance Detection (synthetic
        # detections at the tail have no matching prediction and no bbox).
        for pred, det in zip(predictions, detections, strict=False):
            x1, y1, x2, y2 = pred.bbox
            color = self._class_color(pred.object_class)
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            label = f"{pred.raw_class_name} {pred.confidence:.2f}"
            if det.distance_m < 99.0:
                label += f"  {det.distance_m:.1f}m"
            ((tw, th), baseline) = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            cv2.rectangle(frame, (x1, y1 - th - baseline - 4), (x1 + tw + 4, y1), color, -1)
            cv2.putText(
                frame,
                label,
                (x1 + 2, y1 - baseline - 2),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (255, 255, 255),
                1,
                cv2.LINE_AA,
            )
        return frame

    @staticmethod
    def _class_color(object_class: ObjectClass) -> tuple[int, int, int]:
        palette: dict[ObjectClass, tuple[int, int, int]] = {
            ObjectClass.PERSON: (0, 200, 0),
            ObjectClass.CAR: (0, 140, 255),
            ObjectClass.BICYCLE: (255, 140, 0),
            ObjectClass.MOTORCYCLE: (255, 140, 0),
        }
        return palette.get(object_class, (60, 60, 220))

    def _build_detection(
        self,
        prediction: YoloPrediction,
        lidar_distance_m: float | None,
    ) -> Detection:
        fused, source = fuse_distance_with_source(
            camera_distance_m=prediction.distance_estimate_m,
            lidar_distance_m=lidar_distance_m,
        )
        return Detection(
            object_class=prediction.object_class,
            confidence=prediction.confidence,
            distance_m=fused if fused is not None else 99.0,
            bbox=prediction.bbox,
            distance_source=source,
        )

    def _read_telemetry(self) -> dict[str, object] | None:
        """Return the latest ESP32 telemetry frame, or None if unavailable."""
        if self._telemetry is None:
            return None
        reading = self._telemetry.read()
        if not reading.healthy:
            return None
        return reading.data

    def _synthetic_detection(self, object_class: ObjectClass, distance_m: float) -> Detection:
        # Overhead / drop come from the firmware's ultrasonic flags, which the
        # firmware buzzes but does NOT vibrate for — so the RPi keeps driving
        # vibration here (source is not the forward LiDAR motor path).
        return Detection(
            object_class=object_class,
            confidence=1.0,
            distance_m=distance_m,
            bbox=None,
            timestamp=now_utc(),
            distance_source="ultrasonic",
        )

    def _sleep_for_target_fps(self, loop_start: float) -> None:
        elapsed = time.monotonic() - loop_start
        sleep_s = self._period_s - elapsed
        if sleep_s > 0:
            time.sleep(sleep_s)
