"""Camera sensor wrapping a USB / CSI camera.

Uses OpenCV when available; otherwise produces an unhealthy reading so the
rest of the system can still run on a dev machine without hardware.
"""

from __future__ import annotations

from typing import Any

from core.config import Config
from sensors.base import SensorBase

try:  # OpenCV is optional in dev environments.
    import cv2  # type: ignore[import-not-found]
    import numpy as np  # type: ignore[import-not-found]

    _CV2_AVAILABLE = True
except Exception:  # pragma: no cover
    cv2 = None  # type: ignore[assignment]
    np = None  # type: ignore[assignment]
    _CV2_AVAILABLE = False


class CameraSensor(SensorBase):
    """Captures a single frame from the camera."""

    name = "camera"

    def __init__(
        self,
        device: str | None = None,
        width: int | None = None,
        height: int | None = None,
    ) -> None:
        super().__init__()
        self._device = device if device is not None else Config.CAMERA_DEVICE
        self._width = width if width is not None else Config.CAMERA_WIDTH
        self._height = height if height is not None else Config.CAMERA_HEIGHT
        self._capture: Any = None

    def _initialize_impl(self) -> None:
        if not _CV2_AVAILABLE:
            self._require(False, "OpenCV (cv2) is not installed")

        device: Any = self._device
        if isinstance(device, str) and device.isdigit():
            device = int(device)

        self._capture = cv2.VideoCapture(device)  # type: ignore[union-attr]
        self._capture.set(cv2.CAP_PROP_FRAME_WIDTH, self._width)  # type: ignore[union-attr]
        self._capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self._height)  # type: ignore[union-attr]
        self._require(self._capture.isOpened(), f"cannot open camera {self._device}")

    def _read_impl(self) -> dict[str, Any]:
        self._require(self._capture is not None, "camera not initialized")
        ok, frame = self._capture.read()
        self._require(ok and frame is not None, "frame grab failed")
        return {
            "frame": frame,
            "width": self._width,
            "height": self._height,
        }

    def _close_impl(self) -> None:
        if self._capture is not None:
            self._capture.release()
            self._capture = None
