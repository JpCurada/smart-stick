"""DetectionLoop streaming-decoupling tests.

The video stream must keep getting fresh frames at camera rate even when YOLO
inference is slow — that was the "works then goes black" bug. These tests run
the real capture/detection threads with mocked sensors and a real FrameBuffer.
"""

from __future__ import annotations

import threading
import time
from unittest.mock import MagicMock

import pytest

from detection.detector import DetectionLoop
from detection.frame_buffer import FrameBuffer

pytest.importorskip("numpy")


def _yolo_stub(predict_impl=None) -> MagicMock:
    yolo = MagicMock()
    yolo.load.return_value = None
    yolo.predict.side_effect = predict_impl if predict_impl else (lambda frame: [])
    return yolo


def test_capture_runs_while_yolo_blocks(mock_camera, mock_telemetry) -> None:
    """While a single YOLO call hangs, the capture thread keeps reading the
    camera and refreshing the latest-raw slot — i.e. the video source is
    decoupled from detection. (Doesn't need cv2: asserts on the raw slot, which
    is what feeds FrameBuffer.update.)"""
    release = threading.Event()
    yolo_called = threading.Event()

    def slow_predict(frame):
        yolo_called.set()
        release.wait(timeout=2.0)  # block the detection loop
        return []

    loop = DetectionLoop(
        camera=mock_camera,
        yolo=_yolo_stub(slow_predict),
        telemetry=mock_telemetry,
        frame_buffer=FrameBuffer(),
        fps=30,
    )
    loop.start()
    try:
        assert yolo_called.wait(timeout=1.0), "detection loop never started inference"
        # Detection is now stuck inside slow_predict. The capture thread must
        # still be calling camera.read() repeatedly and refreshing the slot.
        calls_before = mock_camera.read.call_count
        frame_before, _ = loop._latest_capture()
        assert frame_before is not None, "capture loop never populated the raw slot"
        time.sleep(0.2)
        assert mock_camera.read.call_count > calls_before, "capture stalled with detection"
    finally:
        release.set()
        loop.stop(timeout_s=2.0)


def test_annotation_does_not_mutate_raw_frame(mock_camera, mock_telemetry) -> None:
    """Detection annotates a copy, so the shared raw frame is never drawn on."""
    pytest.importorskip("cv2")
    import numpy as np

    from core.types import ObjectClass
    from detection.yolo_model import YoloPrediction

    raw = mock_camera.read.return_value.data["frame"]
    before = raw.copy() if isinstance(raw, np.ndarray) else None

    pred = YoloPrediction(
        object_class=ObjectClass.PERSON,
        raw_class_name="person",
        confidence=0.9,
        bbox=(10, 10, 100, 100),
    )
    loop = DetectionLoop(
        camera=mock_camera,
        yolo=_yolo_stub(lambda frame: [pred]),
        telemetry=mock_telemetry,
        frame_buffer=FrameBuffer(),
        fps=10,
    )
    annotated = loop._annotate_frame(raw, [pred], [MagicMock(distance_m=1.0)])
    if before is not None:
        # Raw frame untouched; annotated is a different array with boxes drawn.
        assert np.array_equal(raw, before)
        assert annotated is not raw
