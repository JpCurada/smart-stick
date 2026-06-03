"""Glues the detection loop to alerts, storage, and output."""

from __future__ import annotations

import threading
import time
import uuid
from collections import deque

from core.types import Detection, SpeechPriority
from detection.alert_engine import AlertDecision, AlertEngine
from detection.detector import DetectionLoop
from services.metrics_service import MetricsService
from services.output_service import OutputService
from storage import (
    AlertRecord,
    AlertRepository,
    DetectionRecord,
    DetectionRepository,
)
from storage.repositories import encode_json
from utils.converters import iso_timestamp, now_utc, unix_timestamp
from utils.logger import get_logger

# How many recent recognitions to keep for the /api/recognition_log feed.
# Mirrors the LSTM navigation buffer so the app's Recognition card scrolls
# the same way the Navigation card does.
_RECOGNITION_LOG_CAPACITY = 100


class DetectionService:
    """Subscribes to detector callbacks and emits alerts + records data."""

    def __init__(
        self,
        loop: DetectionLoop,
        alert_engine: AlertEngine,
        output: OutputService,
        detection_repo: DetectionRepository,
        alert_repo: AlertRepository,
        metrics: MetricsService | None = None,
    ) -> None:
        self._loop = loop
        self._engine = alert_engine
        self._output = output
        self._detection_repo = detection_repo
        self._alert_repo = alert_repo
        self._metrics = metrics
        self._log = get_logger("services.detection")
        self._latest_detections: list[Detection] = []
        self._latest_alert: dict | None = None
        # Rolling history of recognized objects, newest appended last. Filled on
        # every frame a real (bbox-bearing) object is recognized — independent
        # of whether the alert engine fired — so the app's Recognition feed is
        # continuous like the LSTM one, instead of only logging on alerts.
        self._recognition_log: deque[dict] = deque(maxlen=_RECOGNITION_LOG_CAPACITY)
        self._lock = threading.Lock()
        # Additional listeners (e.g. MovementAnalyzer) fan-out from here so
        # the DetectionLoop keeps its single-callback contract.
        self._listeners: list[
            callable  # signature: (detections, meta) -> None
        ] = []
        self._loop.set_callback(self._on_detections)

    def add_listener(self, listener) -> None:
        """Register an extra subscriber. Runs after the core dispatch path.

        Listener failures are logged and swallowed so one bad subscriber
        cannot break detection alerts.
        """
        self._listeners.append(listener)

    def start(self) -> None:
        self._loop.start()

    def stop(self) -> None:
        self._loop.stop()

    def latest_detections(self) -> list[dict]:
        with self._lock:
            return [self._detection_to_dict(d) for d in self._latest_detections]

    def latest_alert(self) -> dict | None:
        with self._lock:
            return dict(self._latest_alert) if self._latest_alert else None

    def fps(self) -> float:
        return self._loop.fps()

    def inference_time_ms(self) -> int:
        return self._loop.last_inference_ms()

    def _on_detections(self, detections: list[Detection], meta: dict) -> None:
        triggered_any = False
        for detection in detections:
            # Log the recognition itself for every real object, whether or not
            # it crosses the alert threshold — this is what feeds the app's
            # continuous Recognition card.
            self._log_recognition(detection)
            decision = self._engine.evaluate(detection)
            if decision.triggered:
                triggered_any = True
                self._dispatch(detection, decision)
                self._record_recognition_metric(detection, meta)

        self._record_detection_metric(detections, meta)
        self._persist_frame(detections, alert_triggered=triggered_any)
        with self._lock:
            self._latest_detections = list(detections)

        for listener in self._listeners:
            try:
                listener(detections, meta)
            except Exception as exc:
                self._log.debug("detection listener failed: %s", exc)

    def _log_recognition(self, detection: Detection) -> None:
        """Append one recognized object to the rolling recognition feed.

        Skips synthetic STAIRS/OVERHEAD detections (no bbox) — those come from
        ultrasonic/firmware flags, not YOLO recognition, and have their own
        alert path. Time-stamped so the app can show "x seconds ago".
        """
        if detection.bbox is None:
            return
        entry = {
            "id": f"rec_{uuid.uuid4().hex[:10]}",
            "timestamp": iso_timestamp(detection.timestamp),
            "object_class": detection.object_class.value,
            "confidence": round(detection.confidence, 3),
            "distance_m": round(detection.distance_m, 2),
        }
        with self._lock:
            self._recognition_log.append(entry)

    def recent_recognitions(self, limit: int) -> list[dict]:
        """Most recent recognitions, newest first. Feeds /api/recognition_log."""
        with self._lock:
            snapshot = list(self._recognition_log)
        snapshot.reverse()
        return snapshot[:limit]

    def _record_recognition_metric(self, detection: Detection, meta: dict) -> None:
        """YOLO recognized + classified one object. Log its inference time."""
        if self._metrics is None or detection.bbox is None:
            return  # synthetic detections (STAIRS / OVERHEAD) have no bbox
        inference_ms = meta.get("inference_ms")
        if inference_ms is None:
            return
        self._metrics.record_obstacle_recognition(
            inference_ms=float(inference_ms),
            object_class=detection.object_class.value,
            distance_m=detection.distance_m,
        )

    def _record_detection_metric(self, detections: list[Detection], meta: dict) -> None:
        """ESP32 confirmed a drop/overhead. Measure SPI→dispatch latency."""
        if self._metrics is None:
            return
        sources: list[str] = meta.get("firmware_flag_sources") or []
        if not sources:
            return
        telemetry_read_at = meta.get("telemetry_read_at")
        if telemetry_read_at is None:
            return
        latency_ms = (time.monotonic() - telemetry_read_at) * 1000.0
        for source in sources:
            self._metrics.record_obstacle_detection(latency_ms=latency_ms, source=source)

    def _dispatch(self, detection: Detection, decision: AlertDecision) -> None:
        # The firmware drives the motor itself for forward LiDAR obstacles
        # (vibrator_update in the ESP32 loop). Sending our own vibrate for the
        # same obstacle would double-drive the motor and fight the firmware's
        # pulse timing, so suppress vibration only when the distance came from
        # the forward LiDAR. Camera-only objects and ultrasonic overhead/drop
        # flags (which the firmware buzzes but does NOT vibrate for) still
        # vibrate from here.
        firmware_vibrates = detection.distance_source == "lidar"
        if decision.vibration is not None and not firmware_vibrates:
            self._output.play_vibration_pattern(decision.vibration, source="detection")
        if decision.tone is not None:
            self._output.play_tone(decision.tone, source="detection")
        if decision.speak_text:
            self._output.speak(
                decision.speak_text, priority="high", source=SpeechPriority.DETECTION
            )
        self._record_alert(detection, decision)

    def _record_alert(self, detection: Detection, decision: AlertDecision) -> None:
        alert_id = f"alert_{uuid.uuid4().hex[:12]}"
        alert_payload = {
            "type": "proximity",
            "object_class": detection.object_class.value,
            "distance_m": round(detection.distance_m, 2),
            "confidence": round(detection.confidence, 3),
            "vibration_pattern": decision.vibration.name if decision.vibration else None,
            "buzzer_frequency_hz": decision.tone.frequency_hz if decision.tone else None,
            "severity": decision.severity.value,
        }
        record = AlertRecord(
            alert_id=alert_id,
            timestamp=now_utc(),
            alert_type="proximity",
            severity=decision.severity.value,
            alert_json=encode_json(alert_payload),
        )
        try:
            self._alert_repo.save(record)
        except Exception as exc:
            self._log.debug("alert save failed: %s", exc)
        with self._lock:
            self._latest_alert = alert_payload

    def _persist_frame(self, detections: list[Detection], alert_triggered: bool) -> None:
        if not detections:
            return
        frame_id = f"frame_{uuid.uuid4().hex[:12]}"
        ts = now_utc()
        payload = {
            "detections": [self._detection_to_dict(d) for d in detections],
        }
        try:
            self._detection_repo.save(
                DetectionRecord(
                    frame_id=frame_id,
                    timestamp=ts,
                    unix_ts=unix_timestamp(ts),
                    detection_json=encode_json(payload),
                    alert_triggered=alert_triggered,
                    object_count=len(detections),
                )
            )
        except Exception as exc:
            self._log.debug("detection save failed: %s", exc)

    @staticmethod
    def _detection_to_dict(detection: Detection) -> dict:
        return {
            "class": detection.object_class.value,
            "confidence": round(detection.confidence, 3),
            "distance_m": round(detection.distance_m, 2),
            "bbox": list(detection.bbox) if detection.bbox else None,
            "timestamp": iso_timestamp(detection.timestamp),
        }
