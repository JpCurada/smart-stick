"""Detection layer: model, fusion, alert decisions, orchestration."""

from detection.alert_engine import AlertDecision, AlertEngine
from detection.detector import DetectionLoop
from detection.distance_fusion import fuse_distance
from detection.patterns import pattern_for_object
from detection.rate_limiter import RateLimiter
from detection.tones import tone_for_alert
from detection.yolo_model import YoloDetector, YoloPrediction

__all__ = [
    "AlertDecision",
    "AlertEngine",
    "DetectionLoop",
    "fuse_distance",
    "pattern_for_object",
    "RateLimiter",
    "tone_for_alert",
    "YoloDetector",
    "YoloPrediction",
]
