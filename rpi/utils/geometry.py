"""Geometry helpers (great-circle distance, intensity scaling)."""

from __future__ import annotations

import math

_EARTH_RADIUS_M: float = 6_371_000.0


def haversine_distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return great-circle distance between two GPS points in meters."""
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return _EARTH_RADIUS_M * c


def distance_to_intensity(
    distance_m: float, max_distance_m: float, max_intensity: int = 255
) -> int:
    """Map distance to vibration intensity. Closer = stronger."""
    if distance_m <= 0:
        return max_intensity
    if distance_m >= max_distance_m:
        return 0
    ratio = 1.0 - (distance_m / max_distance_m)
    return int(round(ratio * max_intensity))
