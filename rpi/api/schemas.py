"""Pydantic request/response schemas for the API."""

from __future__ import annotations

from pydantic import BaseModel, Field

from core.constants import (
    MAX_BUZZER_FREQUENCY,
    MAX_MESSAGE_LENGTH,
    MAX_VIBRATION_INTENSITY,
    MIN_BUZZER_FREQUENCY,
)


class VibrateRequest(BaseModel):
    intensity: int = Field(ge=0, le=MAX_VIBRATION_INTENSITY)
    duration_ms: int = Field(ge=0, le=5000)


class BuzzRequest(BaseModel):
    frequency_hz: int = Field(ge=MIN_BUZZER_FREQUENCY, le=MAX_BUZZER_FREQUENCY)
    duration_ms: int = Field(ge=0, le=5000)


class MessageRequest(BaseModel):
    text: str = Field(min_length=1, max_length=MAX_MESSAGE_LENGTH)
    priority: str = Field(default="normal", pattern="^(low|normal|high)$")


class CommandAck(BaseModel):
    success: bool
    command_id: str | None = None
    message: str | None = None
