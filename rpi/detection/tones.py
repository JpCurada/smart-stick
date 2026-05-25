"""Buzzer tone selection helpers."""

from __future__ import annotations

from core.constants import BUZZER_TONES
from core.types import BuzzerTone, ObjectClass


def tone_for_alert(object_class: ObjectClass) -> BuzzerTone:
    # Overhead = "raise your hand" (high-pitched bursts).
    # Stairs / drop / lower-ultrasonic = "lift the stick" (low-pitched pulse).
    # Everything else = standard.
    if object_class is ObjectClass.OVERHEAD:
        return BUZZER_TONES["overhead_alert"]
    if object_class is ObjectClass.STAIRS:
        return BUZZER_TONES["ground_alert"]
    return BUZZER_TONES["standard_alert"]


def tone_by_name(name: str) -> BuzzerTone:
    if name not in BUZZER_TONES:
        raise KeyError(f"unknown buzzer tone: {name}")
    return BUZZER_TONES[name]
