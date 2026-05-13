"""Text-to-speech output through the audio jack / bluetooth earpiece."""

from __future__ import annotations

from typing import Any

from core.config import Config
from utils.logger import get_logger

try:
    import pyttsx3  # type: ignore[import-not-found]

    _TTS_AVAILABLE = True
except Exception:  # pragma: no cover
    pyttsx3 = None  # type: ignore[assignment]
    _TTS_AVAILABLE = False


class SpeakerController:
    """Wraps pyttsx3. Falls back to logging when TTS is unavailable."""

    def __init__(
        self,
        rate_wpm: int | None = None,
        volume: float | None = None,
    ) -> None:
        self._rate_wpm = rate_wpm if rate_wpm is not None else Config.TTS_RATE_WPM
        self._volume = volume if volume is not None else Config.TTS_VOLUME
        self._engine: Any = None
        self._log = get_logger("output.speaker")
        self._init_engine()

    def _init_engine(self) -> None:
        if not _TTS_AVAILABLE:
            self._log.warning("pyttsx3 unavailable; TTS will log only")
            return
        try:
            self._engine = pyttsx3.init()
            self._engine.setProperty("rate", self._rate_wpm)
            self._engine.setProperty("volume", self._volume)
        except Exception as exc:
            self._log.warning("pyttsx3 init failed: %s", exc)
            self._engine = None

    def speak(self, text: str, priority: str = "normal") -> bool:
        text = text.strip()
        if not text:
            return False
        rate = self._rate_for_priority(priority)
        if self._engine is None:
            self._log.info("TTS(stub) [%s @ %d wpm]: %s", priority, rate, text)
            return True
        try:
            self._engine.setProperty("rate", rate)
            self._engine.say(text)
            self._engine.runAndWait()
            return True
        except Exception as exc:
            self._log.warning("TTS failed: %s", exc)
            return False

    def _rate_for_priority(self, priority: str) -> int:
        if priority == "high":
            return int(self._rate_wpm * 1.2)
        return self._rate_wpm

    def estimate_duration_ms(self, text: str) -> int:
        """Rough estimate: words / (wpm / 60) → seconds → ms."""
        word_count = max(1, len(text.split()))
        seconds = word_count / (self._rate_wpm / 60.0)
        return int(seconds * 1000)
