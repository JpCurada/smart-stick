"""Tests for the detection layer (pure logic, no hardware)."""

from __future__ import annotations

from unittest.mock import MagicMock

from core.types import AlertSeverity, Detection, ObjectClass
from detection.alert_engine import AlertDecision, AlertEngine
from detection.distance_fusion import fuse_distance, fuse_distance_with_source
from detection.patterns import pattern_for_object
from detection.rate_limiter import RateLimiter
from detection.tones import tone_for_alert
from services.detection_service import DetectionService


class TestRateLimiter:
    def test_first_call_passes(self) -> None:
        rl = RateLimiter(cooldown_s=1.0)
        assert rl.allow("k", now_s=0.0)

    def test_second_call_blocks_within_cooldown(self) -> None:
        rl = RateLimiter(cooldown_s=1.0)
        assert rl.allow("k", now_s=0.0)
        assert not rl.allow("k", now_s=0.5)

    def test_call_passes_after_cooldown(self) -> None:
        rl = RateLimiter(cooldown_s=1.0)
        assert rl.allow("k", now_s=0.0)
        assert rl.allow("k", now_s=1.1)

    def test_per_key_isolation(self) -> None:
        rl = RateLimiter(cooldown_s=10.0)
        assert rl.allow("a", now_s=0.0)
        assert rl.allow("b", now_s=0.0)
        assert not rl.allow("a", now_s=1.0)

    def test_reset_clears(self) -> None:
        rl = RateLimiter(cooldown_s=10.0)
        rl.allow("a", now_s=0.0)
        rl.reset("a")
        assert rl.allow("a", now_s=0.1)


class TestDistanceFusion:
    def test_prefers_lidar_when_in_range(self) -> None:
        assert fuse_distance(camera_distance_m=5.0, lidar_distance_m=2.0) == 2.0

    def test_falls_back_to_ultrasonic(self) -> None:
        # LIDAR returns 0 (below valid range) -> use ultrasonic.
        result = fuse_distance(
            camera_distance_m=10.0,
            lidar_distance_m=0.0,
            ultrasonic_distance_m=0.5,
        )
        assert result == 0.5

    def test_falls_back_to_camera(self) -> None:
        result = fuse_distance(camera_distance_m=4.5, lidar_distance_m=None)
        assert result == 4.5

    def test_returns_none_when_all_invalid(self) -> None:
        assert fuse_distance(None, None, None) is None

    def test_source_is_lidar_when_lidar_in_range(self) -> None:
        assert fuse_distance_with_source(camera_distance_m=5.0, lidar_distance_m=2.0) == (
            2.0,
            "lidar",
        )

    def test_source_is_camera_when_only_camera(self) -> None:
        assert fuse_distance_with_source(camera_distance_m=4.5, lidar_distance_m=None) == (
            4.5,
            "camera",
        )

    def test_source_is_none_when_all_invalid(self) -> None:
        assert fuse_distance_with_source(None, None, None) == (None, None)


class TestDispatchMotorOwnership:
    """The firmware owns the motor for forward LiDAR obstacles; the RPi must
    suppress its own vibration only in that case to avoid double-driving."""

    def _service(self) -> tuple[DetectionService, MagicMock]:
        output = MagicMock()
        loop = MagicMock()
        service = DetectionService(
            loop=loop,
            alert_engine=MagicMock(),
            output=output,
            detection_repo=MagicMock(),
            alert_repo=MagicMock(),
        )
        return service, output

    @staticmethod
    def _decision() -> AlertDecision:
        return AlertDecision(
            triggered=True,
            severity=AlertSeverity.HIGH,
            vibration=pattern_for_object(ObjectClass.PERSON),
            tone=tone_for_alert(ObjectClass.PERSON),
            speak_text="person ahead",
        )

    def test_lidar_obstacle_suppresses_rpi_vibration(self) -> None:
        service, output = self._service()
        det = Detection(
            object_class=ObjectClass.PERSON,
            confidence=0.9,
            distance_m=1.5,
            distance_source="lidar",
        )
        service._dispatch(det, self._decision())
        output.play_vibration_pattern.assert_not_called()
        # Buzzer + voice still fire — only the motor is the firmware's job.
        output.play_tone.assert_called_once()
        output.speak.assert_called_once()

    def test_camera_only_obstacle_still_vibrates(self) -> None:
        service, output = self._service()
        det = Detection(
            object_class=ObjectClass.PERSON,
            confidence=0.9,
            distance_m=1.5,
            distance_source="camera",
        )
        service._dispatch(det, self._decision())
        output.play_vibration_pattern.assert_called_once()

    def test_ultrasonic_overhead_still_vibrates(self) -> None:
        service, output = self._service()
        det = Detection(
            object_class=ObjectClass.OVERHEAD,
            confidence=1.0,
            distance_m=0.5,
            distance_source="ultrasonic",
        )
        service._dispatch(det, self._decision())
        output.play_vibration_pattern.assert_called_once()


class TestPatternsAndTones:
    def test_pattern_for_person(self) -> None:
        p = pattern_for_object(ObjectClass.PERSON)
        assert p.intensity == 255
        assert p.name == "single_pulse"

    def test_pattern_for_unknown_class(self) -> None:
        p = pattern_for_object(ObjectClass.UNKNOWN)
        assert p.intensity > 0

    def test_elevation_tone(self) -> None:
        assert tone_for_alert(ObjectClass.STAIRS).frequency_hz == 1500
        assert tone_for_alert(ObjectClass.OVERHEAD).frequency_hz == 1500

    def test_standard_tone(self) -> None:
        assert tone_for_alert(ObjectClass.PERSON).frequency_hz == 1000


class TestAlertEngine:
    def test_close_person_triggers_alert(self) -> None:
        engine = AlertEngine(cooldown_s=0.0)
        detection = Detection(object_class=ObjectClass.PERSON, confidence=0.9, distance_m=1.0)
        decision = engine.evaluate(detection)
        assert decision.triggered
        assert decision.vibration is not None
        assert decision.tone is not None

    def test_distant_person_does_not_trigger(self) -> None:
        engine = AlertEngine(cooldown_s=0.0)
        detection = Detection(object_class=ObjectClass.PERSON, confidence=0.9, distance_m=10.0)
        decision = engine.evaluate(detection)
        assert not decision.triggered

    def test_rate_limited_second_call(self) -> None:
        engine = AlertEngine(cooldown_s=5.0)
        detection = Detection(object_class=ObjectClass.CAR, confidence=0.9, distance_m=1.0)
        first = engine.evaluate(detection)
        second = engine.evaluate(detection)
        assert first.triggered
        assert not second.triggered
        assert second.reason == "cooldown"

    def test_critical_severity_when_very_close(self) -> None:
        engine = AlertEngine(cooldown_s=0.0)
        # Person threshold is 2.0 m; 0.5 m is 25% => CRITICAL.
        detection = Detection(object_class=ObjectClass.PERSON, confidence=0.9, distance_m=0.5)
        decision = engine.evaluate(detection)
        assert decision.severity == AlertSeverity.CRITICAL

    def test_speak_text_includes_distance(self) -> None:
        engine = AlertEngine(cooldown_s=0.0)
        detection = Detection(object_class=ObjectClass.CAR, confidence=0.9, distance_m=1.5)
        decision = engine.evaluate(detection)
        assert decision.speak_text is not None
        assert "1.5" in decision.speak_text
        assert "car" in decision.speak_text
