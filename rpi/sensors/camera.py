"""Camera sensor for the Raspberry Pi CSI camera via Picamera2 (libcamera).

OpenCV's V4L2 backend cannot consume the Pi 5 rp1-cfe nodes, so the CSI
camera is driven through Picamera2 exclusively. On a machine without
Picamera2 the sensor produces an unhealthy reading so the rest of the
system still runs (tests, dev laptop).
"""

from __future__ import annotations

from typing import Any

from core.config import Config
from sensors.base import SensorBase

try:  # libcamera colour conversion only; never required for capture.
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

    def _initialize_impl(self) -> None:
        if not _PICAMERA2_AVAILABLE:
            self._require(False, "Picamera2 is not installed")
        try:
            self._picam = Picamera2()
            config = self._picam.create_video_configuration(
                main={"size": (self._width, self._height), "format": "RGB888"}
            )
            self._picam.configure(config)
            self._picam.start()
            self._log.info("camera using Picamera2 (CSI) %dx%d", self._width, self._height)
        except Exception as exc:
            self._require(False, f"Picamera2 init failed: {exc}")

    def _read_impl(self) -> dict[str, Any]:
        self._require(self._picam is not None, "camera not initialized")
        frame = self._picam.capture_array()
        self._require(frame is not None, "frame grab failed")
        # Picamera2 delivers RGB; OpenCV / YOLO drawing expects BGR.
        if _CV2_AVAILABLE:
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        return {
            "frame": frame,
            "width": self._width,
            "height": self._height,
        }

    def _close_impl(self) -> None:
        if self._picam is not None:
            try:
                self._picam.stop()
                self._picam.close()
            finally:
                self._picam = None
