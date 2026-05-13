"""Tests for the output layer (haptics, buzzer, queue)."""

from __future__ import annotations

import threading
from unittest.mock import MagicMock

from core.types import BuzzerTone, VibrationPattern
from output.buzzer import BuzzerController
from output.haptics import HapticsController
from output.output_queue import OutputCommand, OutputQueue


class TestHapticsController:
    def test_clamps_intensity(self, mock_bridge: MagicMock) -> None:
        controller = HapticsController(bridge=mock_bridge)
        controller.vibrate(intensity=999, duration_ms=100)
        called_intensity = mock_bridge.send_vibration.call_args[0][0]
        assert called_intensity == 255

    def test_negative_duration_is_clamped(self, mock_bridge: MagicMock) -> None:
        controller = HapticsController(bridge=mock_bridge)
        controller.vibrate(intensity=100, duration_ms=-50)
        called_duration = mock_bridge.send_vibration.call_args[0][1]
        assert called_duration == 0

    def test_runs_without_bridge(self) -> None:
        controller = HapticsController(bridge=None)
        assert controller.vibrate(100, 200) is True

    def test_play_pattern_repeats_pulses(self, mock_bridge: MagicMock) -> None:
        controller = HapticsController(bridge=mock_bridge)
        pattern = VibrationPattern(
            name="triple", intensity=200, duration_ms=100, pulses=3, gap_ms=50
        )
        controller.play_pattern(pattern)
        # 3 vibrate pulses + 3 gap calls.
        assert mock_bridge.send_vibration.call_count == 6


class TestBuzzerController:
    def test_clamps_frequency(self, mock_bridge: MagicMock) -> None:
        controller = BuzzerController(bridge=mock_bridge)
        controller.buzz(frequency_hz=10_000, duration_ms=100)
        called_freq = mock_bridge.send_buzz.call_args[0][0]
        assert called_freq == 5000

    def test_play_tone_repeats(self, mock_bridge: MagicMock) -> None:
        controller = BuzzerController(bridge=mock_bridge)
        tone = BuzzerTone(
            name="sos", frequency_hz=2500, duration_ms=500, pattern_count=3, gap_ms=200
        )
        controller.play_tone(tone)
        # 3 tone pulses + 3 gap calls.
        assert mock_bridge.send_buzz.call_count == 6


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
