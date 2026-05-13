"""Combine distance estimates from camera / LIDAR / ultrasonic.

LIDAR is the most precise reading inside its range; ultrasonic provides
overhead and downward coverage; camera-derived distance is used only as a
fallback when neither distance sensor returns a useful number.
"""

from __future__ import annotations

_LIDAR_MIN_M = 0.3
_LIDAR_MAX_M = 40.0
_ULTRASONIC_MIN_M = 0.02
_ULTRASONIC_MAX_M = 4.0


def _is_valid(distance: float | None, low: float, high: float) -> bool:
    return distance is not None and low <= distance <= high


def fuse_distance(
    camera_distance_m: float | None,
    lidar_distance_m: float | None,
    ultrasonic_distance_m: float | None = None,
) -> float | None:
    """Return the most trusted distance reading available."""
    if _is_valid(lidar_distance_m, _LIDAR_MIN_M, _LIDAR_MAX_M):
        return lidar_distance_m
    if _is_valid(ultrasonic_distance_m, _ULTRASONIC_MIN_M, _ULTRASONIC_MAX_M):
        return ultrasonic_distance_m
    if camera_distance_m is not None and camera_distance_m > 0:
        return camera_distance_m
    return None
