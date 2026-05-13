"""YOLO inference wrapper.

Tries to import `ultralytics`; if unavailable the detector still works as a
no-op so tests and dev workflows pass without the ML stack installed.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.config import Config
from core.constants import YOLO_CLASS_MAP
from core.exceptions import DetectionError
from core.types import ObjectClass
from utils.logger import get_logger

try:
    from ultralytics import YOLO  # type: ignore[import-not-found]

    _YOLO_AVAILABLE = True
except Exception:  # pragma: no cover
    YOLO = None  # type: ignore[assignment]
    _YOLO_AVAILABLE = False


@dataclass
class YoloPrediction:
    """One detection produced by the model."""

    object_class: ObjectClass
    raw_class_name: str
    confidence: float
    bbox: tuple[int, int, int, int]  # x1, y1, x2, y2
    distance_estimate_m: float | None = None


class YoloDetector:
    """Loads the YOLO model once and runs inference on numpy frames."""

    def __init__(
        self,
        model_path: str | None = None,
        confidence_threshold: float | None = None,
    ) -> None:
        self._model_path = model_path or Config.YOLO_MODEL_PATH
        self._confidence = (
            confidence_threshold
            if confidence_threshold is not None
            else Config.YOLO_CONFIDENCE_THRESHOLD
        )
        self._model: Any = None
        self._log = get_logger("detection.yolo")

    def load(self) -> bool:
        if not _YOLO_AVAILABLE:
            self._log.warning("ultralytics unavailable; YOLO will return no predictions")
            return False
        try:
            self._model = YOLO(self._model_path)
            self._log.info("loaded YOLO model: %s", self._model_path)
            return True
        except Exception as exc:
            self._log.error("YOLO load failed: %s", exc)
            raise DetectionError(f"could not load YOLO model: {exc}") from exc

    def predict(self, frame: Any) -> list[YoloPrediction]:
        if self._model is None:
            return []
        try:
            results = self._model.predict(
                source=frame,
                conf=self._confidence,
                imgsz=Config.YOLO_IMG_SIZE,
                verbose=False,
            )
        except Exception as exc:
            raise DetectionError(f"inference failed: {exc}") from exc

        predictions: list[YoloPrediction] = []
        for result in results:
            names = getattr(result, "names", {})
            for box in getattr(result, "boxes", []):
                raw_name = names.get(int(box.cls[0]), "unknown")
                predictions.append(
                    YoloPrediction(
                        object_class=YOLO_CLASS_MAP.get(raw_name, ObjectClass.OBSTACLE),
                        raw_class_name=raw_name,
                        confidence=float(box.conf[0]),
                        bbox=tuple(int(v) for v in box.xyxy[0].tolist()),  # type: ignore[arg-type]
                    )
                )
        return predictions
