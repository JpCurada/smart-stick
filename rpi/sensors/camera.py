"""Camera sensor for the Raspberry Pi CSI camera via Picamera2 (libcamera).

OpenCV's V4L2 backend cannot consume the Pi 5 rp1-cfe nodes, so the CSI
camera is driven through Picamera2 exclusively. On a machine without
Picamera2 the sensor produces an unhealthy reading so the rest of the
system still runs (tests, dev laptop).
"""

from __future__ import annotations

import time
from typing import Any

from core.config import Config
from sensors.base import SensorBase

try:  # used only for frame rotation; never required for capture.
    import cv2  # type: ignore[import-not-found]

    _CV2_AVAILABLE = True
except Exception:  # pragma: no cover
    cv2 = None  # type: ignore[assignment]
    _CV2_AVAILABLE = False

try:  # Picamera2 — the only supported capture backend.
    from picamera2 import Picamera2  # type: ignore[import-not-found]

    _PICAMERA2_AVAILABLE = True
except Exception:  # pragma: no cover
    Picamera2 = None  # type: ignore[assignment]
    _PICAMERA2_AVAILABLE = False


class CameraSensor(SensorBase):
    """Captures a single frame from the Pi CSI camera via Picamera2."""

    name = "camera"

    def __init__(
        self,
        device: str | None = None,  # accepted for interface compat; unused
        width: int | None = None,
        height: int | None = None,
    ) -> None:
        super().__init__()
        self._width = width if width is not None else Config.CAMERA_WIDTH
        self._height = height if height is not None else Config.CAMERA_HEIGHT
        self._picam: Any = None
        self._next_retry_at = 0.0
        self._RETRY_BACKOFF_S = 5.0

    def _initialize_impl(self) -> None:
        if not _PICAMERA2_AVAILABLE:
            self._require(False, "Picamera2 is not installed")

        # Back off between attempts so a held camera doesn't trigger a
        # 6 Hz retry storm that leaks file descriptors until ENFILE.
        now = time.monotonic()
        if now < self._next_retry_at:
            self._require(False, "Picamera2 retry backoff")
        self._next_retry_at = now + self._RETRY_BACKOFF_S

        picam = None
        try:
            picam = Picamera2()
            config = picam.create_video_configuration(
                main={"size": (self._width, self._height), "format": "RGB888"}
            )
            picam.configure(config)
            picam.start()
            self._picam = picam
            self._log.info("camera using Picamera2 (CSI) %dx%d", self._width, self._height)
        except Exception as exc:
            # Release any descriptors the partially-built Picamera2 grabbed.
            if picam is not None:
                try:
                    picam.close()
                except Exception:
                    pass
            self._picam = None
            self._require(False, f"Picamera2 init failed: {exc}")

    def _read_impl(self) -> dict[str, Any]:
        self._require(self._picam is not None, "camera not initialized")
        frame = self._picam.capture_array()
        self._require(frame is not None, "frame grab failed")
        # Picamera2's "RGB888" format actually delivers channels in BGR order,
        # which is exactly what OpenCV / YOLO drawing / cv2.imencode expect —
        # so no colour conversion is needed. (Converting here swapped R and B
        # and made the served frame look blue.)
        frame = self._apply_rotation(frame)
        rotated_90 = Config.CAMERA_ROTATION in (90, 270)
        return {
            "frame": frame,
            # Width/height swap when rotated a quarter turn.
            "width": self._height if rotated_90 else self._width,
            "height": self._width if rotated_90 else self._height,
        }

    @staticmethod
    def _apply_rotation(frame: Any) -> Any:
        """Rotate the captured frame clockwise per Config.CAMERA_ROTATION."""
        rotation = Config.CAMERA_ROTATION
        if rotation == 0 or not _CV2_AVAILABLE:
            return frame
        codes = {
            90: cv2.ROTATE_90_CLOCKWISE,
            180: cv2.ROTATE_180,
            270: cv2.ROTATE_90_COUNTERCLOCKWISE,
        }
        code = codes.get(rotation)
        return cv2.rotate(frame, code) if code is not None else frame

    def _close_impl(self) -> None:
        if self._picam is not None:
            try:
                self._picam.stop()
                self._picam.close()
            finally:
                self._picam = None
