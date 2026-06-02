"""Tests for the output layer (haptics, buzzer, queue)."""

from __future__ import annotations

import threading
import time
from unittest.mock import MagicMock

from core.types import BuzzerTone, SpeechPriority, VibrationPattern
from output.buzzer import BuzzerController
from output.haptics import HapticsController
from output.output_queue import OutputCommand, OutputQueue
from services.output_service import OutputService


class TestHapticsController:
    def test_positive_intensity_asserts_on(self) -> None:
        # Assert ON once and stop. The firmware self-clears the motor when
        # the RPi stops asserting ON — sending (and latching) was fine, but
        # there is no standalone OFF command to send.
        link = MagicMock()
        link.send_command.return_value = True
        controller = HapticsController(link=link)
        controller.vibrate(intensity=200, duration_ms=100)
        link.send_command.assert_called_once_with(buzzer_cmd=0, vibrator_cmd=1)

    def test_zero_intensity_is_noop(self) -> None:
        # There is no usable OFF command; intensity 0 sends nothing and the
        # firmware's own vibrator_update turns the motor off.
        link = MagicMock()
        link.send_command.return_value = True
        controller = HapticsController(link=link)
        assert controller.vibrate(intensity=0, duration_ms=100) is True
        link.send_command.assert_not_called()

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


class _GatedSpeaker:
    """Fake speaker whose utterances block until released — lets a test
    hold one utterance 'live' while submitting competing ones.

    Each utterance gets its own release event, and ``stop()`` releases only
    the in-flight one — mirroring how the real engine's stop interrupts the
    current utterance, not future ones."""

    def __init__(self) -> None:
        self.played: list[str] = []
        self._started = threading.Event()
        self._lock = threading.Lock()
        self._current_release: threading.Event | None = None

    def speak(self, text: str, priority: str = "normal") -> bool:
        release = threading.Event()
        with self._lock:
            self.played.append(text)
            self._current_release = release
        self._started.set()
        release.wait(timeout=2.0)
        return True

    def stop(self) -> None:
        # Interrupt only the utterance currently in flight.
        with self._lock:
            if self._current_release is not None:
                self._current_release.set()

    def estimate_duration_ms(self, text: str) -> int:
        return 100

    def wait_started(self, timeout: float = 1.0) -> bool:
        return self._started.wait(timeout=timeout)

    def release(self) -> None:
        with self._lock:
            if self._current_release is not None:
                self._current_release.set()


class TestSpeechHierarchy:
    """Earpiece is a single live slot: strict tier, never a queue.

    Guardian (rank 0) > LSTM (1) > Detection (2). A strictly-higher tier
    drops a newcomer; equal-or-higher interrupts and replaces.
    """

    def _service(self, speaker: _GatedSpeaker) -> tuple[OutputService, OutputQueue]:
        queue = OutputQueue()
        queue.start()
        svc = OutputService(
            haptics=MagicMock(),
            buzzer=MagicMock(),
            speaker=speaker,  # type: ignore[arg-type]
            queue=queue,
            command_repo=MagicMock(),
            message_repo=None,
        )
        return svc, queue

    def test_lower_tier_dropped_while_higher_active(self) -> None:
        speaker = _GatedSpeaker()
        svc, queue = self._service(speaker)
        try:
            svc.speak("guardian here", source=SpeechPriority.GUARDIAN)
            assert speaker.wait_started()  # guardian is live (blocking)
            # LSTM arrives while guardian speaks -> must be DROPPED, not queued.
            svc.speak("lstm nav", source=SpeechPriority.LSTM)
            speaker.release()
            queue.stop()
            assert speaker.played == ["guardian here"]
        finally:
            queue.stop()

    @staticmethod
    def _wait_for(speaker: _GatedSpeaker, text: str, timeout: float = 1.5) -> bool:
        # Release the in-flight utterance repeatedly until `text` plays or we
        # give up — the single worker plays utterances one at a time.
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if text in speaker.played:
                return True
            speaker.release()
            time.sleep(0.02)
        return text in speaker.played

    def test_higher_tier_interrupts_lower(self) -> None:
        speaker = _GatedSpeaker()
        svc, queue = self._service(speaker)
        try:
            svc.speak("detection alert", source=SpeechPriority.DETECTION)
            assert speaker.wait_started()
            # Guardian outranks detection -> interrupts and plays.
            svc.speak("guardian message", source=SpeechPriority.GUARDIAN)
            assert self._wait_for(speaker, "guardian message")
        finally:
            speaker.release()
            queue.stop()

    def test_equal_tier_newest_replaces(self) -> None:
        speaker = _GatedSpeaker()
        svc, queue = self._service(speaker)
        try:
            svc.speak("lstm old", source=SpeechPriority.LSTM)
            assert speaker.wait_started()
            svc.speak("lstm new", source=SpeechPriority.LSTM)
            assert self._wait_for(speaker, "lstm new")
        finally:
            speaker.release()
            queue.stop()
