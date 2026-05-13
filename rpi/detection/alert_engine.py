"""Alert decision logic — pure, side-effect-free, fully testable."""

from __future__ import annotations

from dataclasses import dataclass

from core.config import Config
from core.constants import DISTANCE_THRESHOLDS_M
from core.types import AlertSeverity, BuzzerTone, Detection, VibrationPattern
from detection.patterns import pattern_for_object
from detection.rate_limiter import RateLimiter
from detection.tones import tone_for_alert
from utils.geometry import distance_to_intensity


@dataclass
class AlertDecision:
    """Outcome of an alert evaluation."""

    triggered: bool
    severity: AlertSeverity
    vibration: VibrationPattern | None = None
    tone: BuzzerTone | None = None
    speak_text: str | None = None
    reason: str = ""


class AlertEngine:
    """Decides whether a detection deserves an alert and chooses outputs."""

    def __init__(self, cooldown_s: float | None = None) -> None:
        self._rate_limiter = RateLimiter(
            cooldown_s if cooldown_s is not None else Config.ALERT_COOLDOWN_S
        )

    def evaluate(self, detection: Detection) -> AlertDecision:
        threshold = DISTANCE_THRESHOLDS_M.get(detection.object_class)
        if threshold is None or detection.distance_m > threshold:
            return AlertDecision(
                triggered=False,
                severity=AlertSeverity.LOW,
                reason="outside threshold",
            )

        if not self._rate_limiter.allow(detection.object_class):
            return AlertDecision(
                triggered=False,
                severity=AlertSeverity.LOW,
                reason="cooldown",
            )

        base = pattern_for_object(detection.object_class)
        scaled_intensity = (
            distance_to_intensity(
                detection.distance_m,
                max_distance_m=threshold,
                max_intensity=base.intensity,
            )
            or base.intensity
        )
        vibration = VibrationPattern(
            name=base.name,
            intensity=max(scaled_intensity, 80),
            duration_ms=base.duration_ms,
            pulses=base.pulses,
            gap_ms=base.gap_ms,
        )

        return AlertDecision(
            triggered=True,
            severity=self._severity(detection.distance_m, threshold),
            vibration=vibration,
            tone=tone_for_alert(detection.object_class),
            speak_text=self._speak_text(detection),
            reason="threshold breached",
        )

    @staticmethod
    def _severity(distance_m: float, threshold_m: float) -> AlertSeverity:
        ratio = distance_m / threshold_m if threshold_m else 1.0
        if ratio <= 0.33:
            return AlertSeverity.CRITICAL
        if ratio <= 0.66:
            return AlertSeverity.HIGH
        return AlertSeverity.MEDIUM

    @staticmethod
    def _speak_text(detection: Detection) -> str | None:
        return f"{detection.object_class.value} ahead, {detection.distance_m:.1f} meters"
