"""Background command queue so output never blocks the detection loop."""

from __future__ import annotations

import queue
import threading
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from utils.logger import get_logger


@dataclass
class OutputCommand:
    """A single output operation queued for execution."""

    action: Callable[[], Any]
    name: str = "output"


class OutputQueue:
    """Single-worker FIFO queue executing OutputCommand callables."""

    def __init__(self, max_size: int = 256) -> None:
        self._queue: queue.Queue[OutputCommand | None] = queue.Queue(max_size)
        self._worker: threading.Thread | None = None
        self._stop_flag = threading.Event()
        self._log = get_logger("output.queue")

    def start(self) -> None:
        if self._worker is not None and self._worker.is_alive():
            return
        self._stop_flag.clear()
        self._worker = threading.Thread(target=self._run, name="output-queue", daemon=True)
        self._worker.start()

    def submit(self, command: OutputCommand) -> bool:
        try:
            self._queue.put_nowait(command)
            return True
        except queue.Full:
            self._log.warning("output queue full; dropping %s", command.name)
            return False

    def stop(self, timeout_s: float = 2.0) -> None:
        self._stop_flag.set()
        try:
            self._queue.put_nowait(None)
        except queue.Full:
            pass
        if self._worker is not None:
            self._worker.join(timeout=timeout_s)
            self._worker = None

    def _run(self) -> None:
        while not self._stop_flag.is_set():
            command = self._queue.get()
            if command is None:
                break
            try:
                command.action()
            except Exception as exc:
                self._log.warning("output command %s failed: %s", command.name, exc)


class SpeechChannel:
    """Dedicated single-slot worker for earpiece speech.

    Speech is kept off the shared feedback ``OutputQueue`` so a guardian
    message is never queued behind — or dropped by a full queue of —
    detection vibrate/buzz commands firing at the detection rate.

    There is no FIFO: at most one utterance waits to start. Submitting a new
    one *replaces* any waiting (not-yet-started) utterance, matching the
    strict-hierarchy "single live slot, newest wins" model in OutputService
    (which has already decided drop-vs-play before submitting here). The
    currently-playing utterance is interrupted by OutputService via
    ``speaker.stop()``, not by this channel.
    """

    def __init__(self) -> None:
        self._pending: OutputCommand | None = None
        self._cond = threading.Condition()
        self._worker: threading.Thread | None = None
        self._stop_flag = threading.Event()
        self._log = get_logger("output.speech")

    def start(self) -> None:
        if self._worker is not None and self._worker.is_alive():
            return
        self._stop_flag.clear()
        self._worker = threading.Thread(target=self._run, name="speech-channel", daemon=True)
        self._worker.start()

    def submit(self, command: OutputCommand) -> bool:
        # Single slot: a newer utterance overwrites any waiting one. Never
        # full, never drops the latest — so guardian speech always lands.
        with self._cond:
            self._pending = command
            self._cond.notify()
        return True

    def stop(self, timeout_s: float = 2.0) -> None:
        self._stop_flag.set()
        with self._cond:
            self._cond.notify()
        if self._worker is not None:
            self._worker.join(timeout=timeout_s)
            self._worker = None

    def _run(self) -> None:
        while not self._stop_flag.is_set():
            with self._cond:
                while self._pending is None and not self._stop_flag.is_set():
                    self._cond.wait()
                if self._stop_flag.is_set():
                    break
                command = self._pending
                self._pending = None
            if command is None:
                continue
            try:
                command.action()
            except Exception as exc:
                self._log.warning("speech command %s failed: %s", command.name, exc)
