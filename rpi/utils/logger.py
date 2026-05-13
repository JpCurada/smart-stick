"""Structured logging. One configured logger, reused everywhere."""

from __future__ import annotations

import logging
import sys
from typing import Final

from core.config import Config

_LOG_FORMAT: Final[str] = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"
_DATE_FORMAT: Final[str] = "%Y-%m-%dT%H:%M:%S"

_configured: bool = False


def _configure_root() -> None:
    """Configure root logger once, on first use."""
    global _configured
    if _configured:
        return

    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT))

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(Config.LOG_LEVEL)
    _configured = True


def get_logger(name: str) -> logging.Logger:
    """Return a named logger configured for the application."""
    _configure_root()
    return logging.getLogger(name)
