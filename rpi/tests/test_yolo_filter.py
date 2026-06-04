"""YOLO ignored-class filtering.

Vehicles (car/motorcycle/bus/truck/train) must be dropped during inference so
they produce no bounding box, no alert, and no speech — verify the predict()
filter excludes them while keeping the classes we do care about.
"""

from __future__ import annotations

from types import SimpleNamespace

from core.constants import YOLO_IGNORED_CLASSES
from detection.yolo_model import YoloDetector


def _box(cls_id: int, conf: float = 0.9):
    # Mimic the ultralytics box: .cls[0], .conf[0], .xyxy[0].tolist().
    return SimpleNamespace(
        cls=[cls_id],
        conf=[conf],
        xyxy=[SimpleNamespace(tolist=lambda: [10.0, 10.0, 50.0, 80.0])],
    )


class _FakeModel:
    """Stand-in for a loaded ultralytics model."""

    def __init__(self, names: dict[int, str], boxes: list) -> None:
        self._names = names
        self._boxes = boxes

    def predict(self, **_kwargs):
        return [SimpleNamespace(names=self._names, boxes=self._boxes)]


def test_vehicles_are_dropped() -> None:
    names = {0: "person", 1: "car", 2: "motorcycle", 3: "bicycle", 4: "truck"}
    boxes = [_box(i) for i in names]
    det = YoloDetector()
    det._model = _FakeModel(names, boxes)  # bypass load()

    preds = det.predict(frame=None)
    kept = {p.raw_class_name for p in preds}

    assert kept == {"person", "bicycle"}
    assert not (kept & YOLO_IGNORED_CLASSES)


def test_unmapped_class_becomes_obstacle() -> None:
    # A class that is neither ignored nor explicitly mapped falls back to OBSTACLE.
    names = {0: "backpack"}
    det = YoloDetector()
    det._model = _FakeModel(names, [_box(0)])

    preds = det.predict(frame=None)
    assert len(preds) == 1
    assert preds[0].object_class.value == "obstacle"
    assert preds[0].raw_class_name == "backpack"
