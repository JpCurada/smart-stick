"""Mock LSTM movement analyzer.

Subscribes to detection callbacks and emits richer navigation narration
than the raw alert TTS. Speech goes through OutputService at the LSTM
preemption tier — so guardian messages still interrupt it, and it still
preempts low-priority detection TTS.

This is intentionally heuristic, not ML: it gives a place to plug a real
trained model later while delivering the differentiated UX (positional
narration + suggested action) the spec calls for. The contract — what it
consumes, when it speaks, what it logs — is what a real model would also
honor.
"""

from __future__ import annotations

import threading
import time
import uuid
from collections import deque
from collections.abc import Callable
from typing import Any

from core.types import Detection, ObjectClass, SpeechPriority
from services.output_service import OutputService
from utils.converters import iso_timestamp, now_utc
from utils.logger import get_logger

# Narration cadence: minimum gap between two LSTM utterances. Without
# this the analyzer would fire on every frame the loop produces (~6 Hz)
# and saturate the earpiece.
_MIN_NARRATION_GAP_S = 4.0

# How many recent narrations to keep for the mobile Navigation tab.
_LOG_CAPACITY = 50

# Distance below which the analyzer urges the user to slow down.
_SLOW_DOWN_M = 1.5


class MovementAnalyzer:
    """Heuristic stub for the planned LSTM navigation model."""

    def __init__(
        self,
        output: OutputService,
        frame_width_getter: Callable[[], int | None] | None = None,
    ) -> None:
        self._output = output
        self._frame_width_getter = frame_width_getter
        self._log = get_logger("services.movement")
        self._lock = threading.Lock()
        self._last_narration_at: float = 0.0
        self._log_buffer: deque[dict[str, Any]] = deque(maxlen=_LOG_CAPACITY)

    def on_detections(self, detections: list[Detection], meta: dict) -> None:
        """Detection-loop callback. Picks the most relevant target and narrates."""
        target = self._pick_target(detections)
        if target is None:
            return

        now = time.monotonic()
        with self._lock:
            if now - self._last_narration_at < _MIN_NARRATION_GAP_S:
                return
            self._last_narration_at = now

        frame_width = meta.get("frame_width") or (
            self._frame_width_getter() if self._frame_width_getter else None
        )
        position = self._horizontal_position(target, frame_width)
        suggestion = self._suggestion(target, position)
        text = self._narrate(target, position, suggestion)
        entry = {
            "id": f"nav_{uuid.uuid4().hex[:10]}",
            "timestamp": iso_timestamp(now_utc()),
            "text": text,
            "object_class": target.object_class.value,
            "distance_m": round(target.distance_m, 2),
            "position": position,
            "suggestion": suggestion,
        }
        with self._lock:
            self._log_buffer.append(entry)

        self._output.speak(text, priority="normal", source=SpeechPriority.LSTM)

    def recent(self, limit: int = _LOG_CAPACITY) -> list[dict[str, Any]]:
        """Most recent narrations, newest first. Consumed by /api/navigation_log."""
        with self._lock:
            snapshot = list(self._log_buffer)
        snapshot.reverse()
        return snapshot[:limit]

    @staticmethod
    def _pick_target(detections: list[Detection]) -> Detection | None:
        # Closest detection wins — that's the one the user most needs guidance on.
        # Synthetic STAIRS / OVERHEAD detections have no bbox; they still count.
        if not detections:
            return None
        return min(detections, key=lambda d: d.distance_m)

    @staticmethod
    def _horizontal_position(detection: Detection, frame_width: int | None) -> str:
        if detection.bbox is None or not frame_width:
            return "ahead"
        x1, _, x2, _ = detection.bbox
        center_x = (x1 + x2) / 2
        third = frame_width / 3
        if center_x < third:
            return "left"
        if center_x > 2 * third:
            return "right"
        return "ahead"

    @staticmethod
    def _suggestion(detection: Detection, position: str) -> str:
        cls = detection.object_class
        if cls is ObjectClass.OVERHEAD:
            return "lower your head"
        if cls is ObjectClass.STAIRS:
            return "lift the stick"
        if detection.distance_m <= _SLOW_DOWN_M:
            if position == "left":
                return "step right"
            if position == "right":
                return "step left"
            return "slow down"
        return "stay alert"

    @staticmethod
    def _narrate(detection: Detection, position: str, suggestion: str) -> str:
        cls_name = detection.object_class.value
        distance = detection.distance_m
        if position == "ahead":
            location_phrase = f"{distance:.1f} meters ahead"
        else:
            location_phrase = f"on your {position}, {distance:.1f} meters away"
        return f"{cls_name} {location_phrase} — {suggestion}"
