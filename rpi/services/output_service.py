"""Orchestrates output devices via the background queue and records commands."""

from __future__ import annotations

import json
import threading
import time
import uuid
from collections.abc import Callable

from core.constants import BUZZER_TONES
from core.types import BuzzerTone, SpeechPriority, VibrationPattern
from output import (
    BuzzerController,
    HapticsController,
    OutputCommand,
    OutputQueue,
    SpeakerController,
)
from storage import CommandRecord, CommandRepository, MessageRecord, MessageRepository
from utils.converters import now_utc
from utils.logger import get_logger

# How long Find My Stick suppresses detection haptics + buzzer after trigger.
# Matches the firmware override pattern so the cane keeps buzzing/vibrating
# for the full window without competing detection commands interleaving.
FIND_MY_STICK_BLOCK_SECONDS = 30.0


def _command_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


class OutputService:
    """High-level API for triggering outputs. Persists every command."""

    def __init__(
        self,
        haptics: HapticsController,
        buzzer: BuzzerController,
        speaker: SpeakerController,
        queue: OutputQueue,
        command_repo: CommandRepository,
        message_repo: MessageRepository | None = None,
    ) -> None:
        self._haptics = haptics
        self._buzzer = buzzer
        self._speaker = speaker
        self._queue = queue
        self._commands = command_repo
        self._messages = message_repo
        self._log = get_logger("services.output")
        # Earpiece is a single live slot — strict hierarchy, never a queue.
        # At most one utterance is "current" at a time. A new speak() either:
        #   • plays now (its tier >= the current tier) — interrupting the
        #     current utterance, including a same-tier one (newest wins); or
        #   • is dropped immediately (a strictly higher tier is current).
        # We never buffer speech: lower/late items vanish, they do not wait.
        # `_speech_generation` is bumped on every accepted speak so a stale
        # queued action knows it has been superseded and skips playing.
        self._speech_lock = threading.Lock()
        self._active_speech_priority: SpeechPriority | None = None
        self._speech_generation = 0
        # Find My Stick suppression window. SOS suppression is checked via
        # _sos_active_getter (set by the container) so we don't take a hard
        # dep on SosService here.
        self._find_active_until: float = 0.0
        self._sos_active_getter: Callable[[], bool] | None = None

    def set_sos_active_getter(self, getter: Callable[[], bool]) -> None:
        """Wire in a callable returning True while the SOS button is held."""
        self._sos_active_getter = getter

    def feedback_suppressed(self) -> bool:
        """True when SOS is held OR the Find My Stick window is still open."""
        if time.monotonic() < self._find_active_until:
            return True
        getter = self._sos_active_getter
        if getter is not None:
            try:
                return bool(getter())
            except Exception:
                return False
        return False

    def trigger_vibration(self, intensity: int, duration_ms: int, *, source: str = "manual") -> str:
        command_id = _command_id("cmd_vib")
        params = {"intensity": int(intensity), "duration_ms": int(duration_ms)}
        if source == "detection" and self.feedback_suppressed():
            self._log.debug("vibrate suppressed by SOS/Find window")
            return command_id

        def action() -> None:
            ok = self._haptics.vibrate(intensity, duration_ms)
            self._record(command_id, "vibrate", params, ok)

        self._queue.submit(OutputCommand(action=action, name="vibrate"))
        return command_id

    def play_vibration_pattern(
        self, pattern: VibrationPattern, *, source: str = "detection"
    ) -> str:
        command_id = _command_id("cmd_pat")
        params = {
            "intensity": pattern.intensity,
            "duration_ms": pattern.duration_ms,
            "pulses": pattern.pulses,
            "gap_ms": pattern.gap_ms,
            "name": pattern.name,
        }
        if source == "detection" and self.feedback_suppressed():
            self._log.debug("pattern %s suppressed by SOS/Find window", pattern.name)
            return command_id

        def action() -> None:
            ok = self._haptics.play_pattern(pattern)
            self._record(command_id, "vibrate", params, ok)

        self._queue.submit(OutputCommand(action=action, name=f"pattern:{pattern.name}"))
        return command_id

    def trigger_buzz(self, frequency_hz: int, duration_ms: int, *, source: str = "manual") -> str:
        command_id = _command_id("cmd_buz")
        params = {"frequency_hz": int(frequency_hz), "duration_ms": int(duration_ms)}
        if source == "detection" and self.feedback_suppressed():
            self._log.debug("buzz suppressed by SOS/Find window")
            return command_id

        def action() -> None:
            ok = self._buzzer.buzz(frequency_hz, duration_ms)
            self._record(command_id, "buzz", params, ok)

        self._queue.submit(OutputCommand(action=action, name="buzz"))
        return command_id

    def play_tone(self, tone: BuzzerTone, *, source: str = "system") -> str:
        command_id = _command_id("cmd_tone")
        params = {
            "frequency_hz": tone.frequency_hz,
            "duration_ms": tone.duration_ms,
            "pattern_count": tone.pattern_count,
            "name": tone.name,
        }
        if source == "detection" and self.feedback_suppressed():
            self._log.debug("tone %s suppressed by SOS/Find window", tone.name)
            return command_id

        def action() -> None:
            ok = self._buzzer.play_tone(tone)
            self._record(command_id, "buzz", params, ok)

        self._queue.submit(OutputCommand(action=action, name=f"tone:{tone.name}"))
        return command_id

    def speak(
        self,
        text: str,
        priority: str = "normal",
        *,
        source: SpeechPriority = SpeechPriority.GUARDIAN,
    ) -> str:
        """Queue text for the earpiece.

        ``priority`` is the TTS *urgency* (low/normal/high) — controls speech
        rate, passed straight through to the speaker. ``source`` is the
        *preemption tier* (guardian > LSTM > detection) — determines whether
        this utterance interrupts or is interrupted by others. Defaults to
        guardian so direct callers without explicit source preempt by default.
        """
        message_id = _command_id("msg")
        params = {"text": text, "priority": priority, "source": source.value}
        speech_priority = source

        # Strict hierarchy, single live slot — no queue. Drop the newcomer
        # only if a STRICTLY higher tier is currently speaking. Otherwise it
        # wins: equal-or-higher tier interrupts whatever is live (newest wins
        # at equal tier). `my_gen` lets the queued action detect that an even
        # newer speak superseded it before it got a turn.
        with self._speech_lock:
            active = self._active_speech_priority
            if active is not None and speech_priority.rank > active.rank:
                self._log.debug(
                    "speech %s (%s) dropped — %s is speaking",
                    message_id,
                    speech_priority.value,
                    active.value,
                )
                return message_id
            self._speech_generation += 1
            my_gen = self._speech_generation
            self._active_speech_priority = speech_priority

        # Interrupt whatever is mid-utterance so the winner is heard at once.
        self._speaker.stop()

        def action() -> None:
            with self._speech_lock:
                if my_gen != self._speech_generation:
                    # A newer speak() superseded this one before it played.
                    self._log.debug("speech %s superseded before play", message_id)
                    return
            try:
                ok = self._speaker.speak(text, priority=priority)
            finally:
                with self._speech_lock:
                    if my_gen == self._speech_generation:
                        self._active_speech_priority = None
            self._record(message_id, "speak", params, ok)
            if self._messages is not None and ok:
                self._messages.mark_delivered(message_id)

        if self._messages is not None:
            self._messages.save(
                MessageRecord(
                    message_id=message_id,
                    timestamp=now_utc(),
                    text=text[:500],
                    priority=priority,
                    tts_engine="pyttsx3",
                    estimated_speak_time_ms=self._speaker.estimate_duration_ms(text),
                )
            )
        self._queue.submit(OutputCommand(action=action, name="speak"))
        return message_id

    def emergency_sos(self) -> str:
        return self.play_tone(BUZZER_TONES["emergency_sos"], source="system")

    def find_my_stick(self) -> str:
        """Buzz + vibrate the cane so a sighted helper can locate it.

        Opens a FIND_MY_STICK_BLOCK_SECONDS window during which detection
        haptics + buzzer are suppressed (see feedback_suppressed). Earpiece
        TTS is unaffected — guardian messages still come through.
        """
        command_id = _command_id("cmd_find")
        params = {"buzzer_cmd": 1, "vibrator_cmd": 1, "name": "find_my_stick"}
        self._find_active_until = time.monotonic() + FIND_MY_STICK_BLOCK_SECONDS

        def action() -> None:
            buzzer_ok = self._buzzer.play_tone(BUZZER_TONES["standard_alert"])
            haptics_ok = self._haptics.vibrate(intensity=255, duration_ms=500)
            self._record(command_id, "find_my_stick", params, buzzer_ok and haptics_ok)

        self._queue.submit(OutputCommand(action=action, name="find_my_stick"))
        return command_id

    def _record(
        self,
        command_id: str,
        command_type: str,
        params: dict,
        ok: bool,
    ) -> None:
        try:
            self._commands.save(
                CommandRecord(
                    command_id=command_id,
                    timestamp=now_utc(),
                    command_type=command_type,
                    params_json=json.dumps(params, separators=(",", ":")),
                    sent_to_esp32=ok,
                    ack_received=ok,
                )
            )
        except Exception as exc:
            self._log.debug("could not record command %s: %s", command_id, exc)
