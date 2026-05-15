"""Thread-safe single-slot buffer holding the most recent JPEG frame.

The detection loop writes into this buffer on every processed frame; the
HTTP layer reads from it to serve `/api/latest_frame`. Only the latest
frame is retained — readers never block the writer.
"""

from __future__ import annotations

import threading
from typing import Any

from utils.logger import get_logger

try:
    import cv2  # type: ignore[import-not-found]

    _CV2_AVAILABLE = True
except Exception:  # pragma: no cover
    cv2 = None  # type: ignore[assignment]
    _CV2_AVAILABLE = False


class FrameBuffer:
    """Single-slot buffer of JPEG-encoded camera frames."""

    def __init__(self, jpeg_quality: int = 70) -> None:
        self._jpeg: bytes | None = None
        self._timestamp: float = 0.0
        self._lock = threading.Lock()
        self._quality = jpeg_quality
        self._log = get_logger("detection.frame_buffer")

    def update(self, frame: Any, timestamp: float) -> None:
        """Encode and store a frame. Silently drops if cv2 is missing."""
        if not _CV2_AVAILABLE or frame is None:
            return
        try:
            ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, self._quality])
            if not ok:
                return
            jpeg_bytes = buf.tobytes()
        except Exception as exc:
            self._log.debug("jpeg encode failed: %s", exc)
            return
        with self._lock:
            self._jpeg = jpeg_bytes
            self._timestamp = timestamp

    def latest(self) -> tuple[bytes | None, float]:
        with self._lock:
            return self._jpeg, self._timestamp
