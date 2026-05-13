"""Abstract base class shared by every hardware sensor.

Each concrete sensor implements `_read_impl()` returning a payload dict;
the base class handles error wrapping, health tracking, and timestamps so
implementations stay short and focused on hardware specifics.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from core.exceptions import SensorError
from core.types import SensorReading
from utils.converters import now_utc
from utils.logger import get_logger


@dataclass
class SensorStatus:
    """Lightweight health report for a sensor."""

    name: str
    healthy: bool
    last_error: str | None = None
    consecutive_failures: int = 0


class SensorBase(ABC):
    """Standard interface every sensor implements."""

    name: str = "sensor"

    def __init__(self) -> None:
        self._log = get_logger(f"sensors.{self.name}")
        self._status = SensorStatus(name=self.name, healthy=False)
        self._initialized = False

    def initialize(self) -> None:
        """Perform one-time hardware setup. Safe to call multiple times."""
        if self._initialized:
            return
        try:
            self._initialize_impl()
            self._initialized = True
            self._status.healthy = True
            self._log.info("%s initialized", self.name)
        except Exception as exc:
            self._status.healthy = False
            self._status.last_error = str(exc)
            self._log.warning("%s initialization failed: %s", self.name, exc)

    def read(self) -> SensorReading:
        """Read one sample. Never raises — failures become unhealthy readings."""
        if not self._initialized:
            self.initialize()

        timestamp = now_utc()
        try:
            data = self._read_impl()
            self._status.healthy = True
            self._status.consecutive_failures = 0
            self._status.last_error = None
            return SensorReading(
                sensor_name=self.name,
                timestamp=timestamp,
                data=data,
                healthy=True,
            )
        except Exception as exc:
            self._status.consecutive_failures += 1
            self._status.healthy = False
            self._status.last_error = str(exc)
            self._log.debug("%s read failed: %s", self.name, exc)
            return SensorReading(
                sensor_name=self.name,
                timestamp=timestamp,
                data={},
                healthy=False,
                error=str(exc),
            )

    def is_healthy(self) -> bool:
        return self._status.healthy

    def status(self) -> SensorStatus:
        return self._status

    def close(self) -> None:
        """Release hardware resources. Override if needed."""
        try:
            self._close_impl()
        except Exception as exc:
            self._log.debug("%s close raised: %s", self.name, exc)
        self._initialized = False

    @abstractmethod
    def _read_impl(self) -> dict[str, Any]:
        """Subclasses return the raw payload dict here."""

    def _initialize_impl(self) -> None:
        """Override for setup logic. Default no-op."""

    def _close_impl(self) -> None:
        """Override for teardown logic. Default no-op."""

    def _require(self, condition: bool, message: str) -> None:
        if not condition:
            raise SensorError(f"{self.name}: {message}")
