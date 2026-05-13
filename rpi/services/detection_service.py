"""Glues the detection loop to alerts, storage, and output."""

from __future__ import annotations

import threading
import uuid

from core.types import Detection
from detection.alert_engine import AlertDecision, AlertEngine
from detection.detector import DetectionLoop
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


class DetectionService:
    """Subscribes to detector callbacks and emits alerts + records data."""

    def __init__(
        self,
        loop: DetectionLoop,
        alert_engine: AlertEngine,
        output: OutputService,
        detection_repo: DetectionRepository,
        alert_repo: AlertRepository,
    ) -> None:
        self._loop = loop
        self._engine = alert_engine
        self._output = output
        self._detection_repo = detection_repo
        self._alert_repo = alert_repo
        self._log = get_logger("services.detection")
        self._latest_detections: list[Detection] = []
        self._latest_alert: dict | None = None
        self._lock = threading.Lock()
        self._loop.set_callback(self._on_detections)

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
            decision = self._engine.evaluate(detection)
            if decision.triggered:
                triggered_any = True
                self._dispatch(detection, decision)

        self._persist_frame(detections, alert_triggered=triggered_any)
        with self._lock:
            self._latest_detections = list(detections)

    def _dispatch(self, detection: Detection, decision: AlertDecision) -> None:
        if decision.vibration is not None:
            self._output.play_vibration_pattern(decision.vibration)
        if decision.tone is not None:
            self._output.play_tone(decision.tone)
        if decision.speak_text:
            self._output.speak(decision.speak_text, priority="high")
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
