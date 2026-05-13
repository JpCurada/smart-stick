"""Lookup helpers for vibration patterns. The data lives in core/constants."""

from __future__ import annotations

from core.constants import VIBRATION_PATTERNS
from core.types import ObjectClass, VibrationPattern


def pattern_for_object(object_class: ObjectClass) -> VibrationPattern:
    """Return the vibration pattern configured for an object class."""
    return VIBRATION_PATTERNS.get(object_class, VIBRATION_PATTERNS[ObjectClass.UNKNOWN])
