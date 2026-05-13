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
