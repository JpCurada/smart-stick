"""Inbound TTS messages from the caregiver app."""

from __future__ import annotations

from core.constants import MAX_MESSAGE_LENGTH
from services.output_service import OutputService
from storage import MessageRepository
from utils.logger import get_logger


class MessageService:
    """Validate, queue, and persist caregiver messages."""

    def __init__(self, output: OutputService, repository: MessageRepository) -> None:
        self._output = output
        self._repo = repository
        self._log = get_logger("services.message")

    def send(self, text: str, priority: str = "normal") -> dict:
        text = (text or "").strip()
        if not text:
            raise ValueError("message text cannot be empty")
        if len(text) > MAX_MESSAGE_LENGTH:
            text = text[:MAX_MESSAGE_LENGTH]
        message_id = self._output.speak(text, priority=priority)
        return {
            "message_id": message_id,
            "text": text,
            "priority": priority,
            "delivered": False,
        }

    def history(self, limit: int = 20) -> list[dict]:
        return self._repo.history(limit=limit)
