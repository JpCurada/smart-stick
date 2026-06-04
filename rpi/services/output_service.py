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
    SpeechChannel,
)
from sensors.esp32_spi import Esp32SpiLink
from storage import CommandRecord, CommandRepository, MessageRecord, MessageRepository
from utils.converters import now_utc
from utils.logger import get_logger

# How long Find My Stick suppresses detection haptics + buzzer after trigger.
# Matches the firmware override pattern so the cane keeps buzzing/vibrating
# for the full window without competing detection commands interleaving.
FIND_MY_STICK_BLOCK_SECONDS = 30.0

# How long the cane actively buzzes + vibrates for one Find press, and how
# often the RPi re-asserts the override. The ESP32 re-runs its own buzzer /
# vibrator self-update every firmware loop and would cancel a one-shot
# override on the very next loop, so the RPi must re-send the command faster
# than the firmware loops (~tens of ms) to keep the cane alerting.
FIND_ALERT_DURATION_S = 2.0
FIND_REASSERT_INTERVAL_S = 0.03

# Combined Find override frame: drop-pattern buzzer + vibrator on. Sent as a
# single SPI command so neither output cancels the other (a buzz-only frame
# carries vibrator_cmd=0 and vice-versa).
_FIND_BUZZER_CMD = 1  # BUZZER_DROP
_FIND_VIBRATOR_CMD = 1  # vibrator on


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
        speech_channel: SpeechChannel | None = None,
        link: Esp32SpiLink | None = None,
    ) -> None:
        self._haptics = haptics
        self._buzzer = buzzer
        self._speaker = speaker
        self._queue = queue
        # Shared SPI link, used directly only by Find My Stick, which must
        # re-assert a COMBINED buzz+vibrate frame repeatedly (see find_my_stick).
        self._link = link
        self._find_thread: threading.Thread | None = None
        self._find_stop = threading.Event()
        # Speech runs on its own single-slot channel, NOT the shared feedback
        # queue — so guardian/LSTM/detection speech is never queued behind or
        # dropped by the flood of detection vibrate/buzz commands ("output
        # queue full"). The channel is started lazily on first speak().
        self._speech = speech_channel if speech_channel is not None else SpeechChannel()
        self._speech_started = False
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

    def stop(self) -> None:
        """Stop the speech channel and any Find alert. Called on shutdown."""
        self._stop_find_thread()
        if self._speech_started:
            self._speech.stop()
            self._speech_started = False

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

        # Strict hierarchy, single live slot — no queue. A newcomer wins ONLY
        # if it is a STRICTLY higher tier than what's currently speaking; then
        # it interrupts so the more important message is heard at once. At
        # equal tier (e.g. one detection alert after another) we let the
        # current utterance FINISH and drop the newcomer — otherwise rapid
        # detections keep cutting each other off and you hear clipped fragments
        # ("obst— obst—") instead of complete "obstacle ahead, N meters"
        # phrases. `my_gen` lets the queued action detect that an even newer
        # higher-tier speak superseded it before it got a turn.
        with self._speech_lock:
            active = self._active_speech_priority
            if active is not None and speech_priority.rank >= active.rank:
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

        # Interrupt whatever is mid-utterance so the higher-tier winner is heard.
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
        # Speech goes on its dedicated single-slot channel, never the shared
        # feedback queue — so it cannot be dropped by "output queue full".
        if not self._speech_started:
            self._speech.start()
            self._speech_started = True
        self._speech.submit(OutputCommand(action=action, name="speak"))
        return message_id

    def emergency_sos(self) -> str:
        return self.play_tone(BUZZER_TONES["emergency_sos"], source="system")

    def find_my_stick(self, mode: str = "both") -> str:
        """Alert the cane so a sighted helper can locate it.

        ``mode`` selects which outputs fire:
          • "both"    — buzz + vibrate (default)
          • "vibrate" — vibrator only, buzzer silent
          • "buzz"    — buzzer only, vibrator still

        The ESP32 re-runs its own buzzer/vibrator self-update every firmware
        loop and cancels a one-shot RPi override on the very next loop, so a
        single command produces at most an inaudible blip. Instead we run a
        short-lived thread that re-asserts the selected frame every
        FIND_REASSERT_INTERVAL_S for FIND_ALERT_DURATION_S — faster than the
        firmware loops — so the cane keeps alerting for the full window.

        Also opens a FIND_MY_STICK_BLOCK_SECONDS window during which detection
        haptics + buzzer are suppressed (see feedback_suppressed). Earpiece
        TTS is unaffected — guardian messages still come through.
        """
        buzzer_cmd = _FIND_BUZZER_CMD if mode in ("both", "buzz") else 0
        vibrator_cmd = _FIND_VIBRATOR_CMD if mode in ("both", "vibrate") else 0

        command_id = _command_id("cmd_find")
        params = {
            "buzzer_cmd": buzzer_cmd,
            "vibrator_cmd": vibrator_cmd,
            "duration_s": FIND_ALERT_DURATION_S,
            "name": "find_my_stick",
            "mode": mode,
        }
        self._find_active_until = time.monotonic() + FIND_MY_STICK_BLOCK_SECONDS

        # Cancel any in-flight Find so a new press restarts cleanly.
        self._stop_find_thread()
        self._find_stop.clear()
        self._find_thread = threading.Thread(
            target=self._run_find_alert,
            args=(buzzer_cmd, vibrator_cmd),
            name="find-my-stick",
            daemon=True,
        )
        self._find_thread.start()

        self._record(command_id, "find_my_stick", params, self._link is not None)
        return command_id

    def _run_find_alert(self, buzzer_cmd: int, vibrator_cmd: int) -> None:
        """Re-assert the selected Find override until the duration elapses."""
        if self._link is None:
            # No hardware link (dev/test) — nothing to drive.
            self._log.info(
                "find(no link) buzz=%d vib=%d for %.1fs",
                buzzer_cmd,
                vibrator_cmd,
                FIND_ALERT_DURATION_S,
            )
            return
        deadline = time.monotonic() + FIND_ALERT_DURATION_S
        while not self._find_stop.is_set() and time.monotonic() < deadline:
            self._link.send_command(buzzer_cmd=buzzer_cmd, vibrator_cmd=vibrator_cmd)
            time.sleep(FIND_REASSERT_INTERVAL_S)

    def _stop_find_thread(self) -> None:
        self._find_stop.set()
        thread = self._find_thread
        if thread is not None and thread.is_alive() and thread is not threading.current_thread():
            thread.join(timeout=FIND_ALERT_DURATION_S + 0.5)
        self._find_thread = None

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
