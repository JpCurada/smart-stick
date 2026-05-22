"""Tests for the output layer (haptics, buzzer, queue)."""

from __future__ import annotations

import threading
from unittest.mock import MagicMock

from core.types import BuzzerTone, VibrationPattern
from output.buzzer import BuzzerController
from output.haptics import HapticsController
from output.output_queue import OutputCommand, OutputQueue


class TestHapticsController:
    def test_positive_intensity_turns_motor_on(self) -> None:
        link = MagicMock()
        link.send_command.return_value = True
        controller = HapticsController(link=link)
        controller.vibrate(intensity=200, duration_ms=100)
        link.send_command.assert_called_once_with(buzzer_cmd=0, vibrator_cmd=1)

    def test_zero_intensity_turns_motor_off(self) -> None:
        link = MagicMock()
        link.send_command.return_value = True
        controller = HapticsController(link=link)
        controller.vibrate(intensity=0, duration_ms=100)
        link.send_command.assert_called_once_with(buzzer_cmd=0, vibrator_cmd=0)

    def test_runs_without_link(self) -> None:
        controller = HapticsController(link=None)
        assert controller.vibrate(100, 200) is True

    def test_play_pattern_asserts_on_override(self) -> None:
        link = MagicMock()
        link.send_command.return_value = True
        controller = HapticsController(link=link)
        pattern = VibrationPattern(
            name="triple", intensity=200, duration_ms=100, pulses=3, gap_ms=50
        )
        controller.play_pattern(pattern)
        link.send_command.assert_called_once_with(buzzer_cmd=0, vibrator_cmd=1)


class TestBuzzerController:
    def test_buzz_selects_drop_pattern(self) -> None:
        link = MagicMock()
        link.send_command.return_value = True
        controller = BuzzerController(link=link)
        controller.buzz(frequency_hz=1000, duration_ms=100)
        link.send_command.assert_called_once_with(buzzer_cmd=1, vibrator_cmd=0)

    def test_sos_tone_maps_to_sos_mode(self) -> None:
        link = MagicMock()
        link.send_command.return_value = True
        controller = BuzzerController(link=link)
        tone = BuzzerTone(
            name="emergency_sos",
            frequency_hz=2500,
            duration_ms=500,
            pattern_count=3,
            gap_ms=200,
        )
        controller.play_tone(tone)
        link.send_command.assert_called_once_with(buzzer_cmd=3, vibrator_cmd=0)

    def test_runs_without_link(self) -> None:
        controller = BuzzerController(link=None)
        tone = BuzzerTone(name="standard_alert", frequency_hz=1000, duration_ms=200)
        assert controller.play_tone(tone) is True


class TestOutputQueue:
    def test_command_executes_on_worker(self) -> None:
        queue = OutputQueue()
        queue.start()
        called = threading.Event()

        def action() -> None:
            called.set()

        queue.submit(OutputCommand(action=action, name="test"))
        assert called.wait(timeout=1.0)
        queue.stop()

    def test_errors_do_not_kill_worker(self) -> None:
        queue = OutputQueue()
        queue.start()

        def explode() -> None:
            raise RuntimeError("boom")

        ok = threading.Event()

        def good() -> None:
            ok.set()

        queue.submit(OutputCommand(action=explode, name="bad"))
        queue.submit(OutputCommand(action=good, name="good"))
        assert ok.wait(timeout=1.0)
        queue.stop()
