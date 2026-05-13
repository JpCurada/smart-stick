"""Buzzer tone selection helpers."""

from __future__ import annotations

from core.constants import BUZZER_TONES
from core.types import BuzzerTone, ObjectClass

_ELEVATION_CLASSES = {ObjectClass.STAIRS, ObjectClass.OVERHEAD}


def tone_for_alert(object_class: ObjectClass) -> BuzzerTone:
    if object_class in _ELEVATION_CLASSES:
        return BUZZER_TONES["elevation_alert"]
    return BUZZER_TONES["standard_alert"]


def tone_by_name(name: str) -> BuzzerTone:
    if name not in BUZZER_TONES:
        raise KeyError(f"unknown buzzer tone: {name}")
    return BUZZER_TONES[name]
