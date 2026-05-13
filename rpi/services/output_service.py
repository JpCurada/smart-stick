"""Orchestrates output devices via the background queue and records commands."""

from __future__ import annotations

import json
import uuid

from core.constants import BUZZER_TONES
from core.types import BuzzerTone, VibrationPattern
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

    def trigger_vibration(self, intensity: int, duration_ms: int) -> str:
        command_id = _command_id("cmd_vib")
        params = {"intensity": int(intensity), "duration_ms": int(duration_ms)}

        def action() -> None:
            ok = self._haptics.vibrate(intensity, duration_ms)
            self._record(command_id, "vibrate", params, ok)

        self._queue.submit(OutputCommand(action=action, name="vibrate"))
        return command_id

    def play_vibration_pattern(self, pattern: VibrationPattern) -> str:
        command_id = _command_id("cmd_pat")
        params = {
            "intensity": pattern.intensity,
            "duration_ms": pattern.duration_ms,
            "pulses": pattern.pulses,
            "gap_ms": pattern.gap_ms,
            "name": pattern.name,
        }

        def action() -> None:
            ok = self._haptics.play_pattern(pattern)
            self._record(command_id, "vibrate", params, ok)

        self._queue.submit(OutputCommand(action=action, name=f"pattern:{pattern.name}"))
        return command_id

    def trigger_buzz(self, frequency_hz: int, duration_ms: int) -> str:
        command_id = _command_id("cmd_buz")
        params = {"frequency_hz": int(frequency_hz), "duration_ms": int(duration_ms)}

        def action() -> None:
            ok = self._buzzer.buzz(frequency_hz, duration_ms)
            self._record(command_id, "buzz", params, ok)

        self._queue.submit(OutputCommand(action=action, name="buzz"))
        return command_id

    def play_tone(self, tone: BuzzerTone) -> str:
        command_id = _command_id("cmd_tone")
        params = {
            "frequency_hz": tone.frequency_hz,
            "duration_ms": tone.duration_ms,
            "pattern_count": tone.pattern_count,
            "name": tone.name,
        }

        def action() -> None:
            ok = self._buzzer.play_tone(tone)
            self._record(command_id, "buzz", params, ok)

        self._queue.submit(OutputCommand(action=action, name=f"tone:{tone.name}"))
        return command_id

    def speak(self, text: str, priority: str = "normal") -> str:
        message_id = _command_id("msg")
        params = {"text": text, "priority": priority}

        def action() -> None:
            ok = self._speaker.speak(text, priority=priority)
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
        return self.play_tone(BUZZER_TONES["emergency_sos"])

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
