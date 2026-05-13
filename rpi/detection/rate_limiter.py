"""Per-key cooldown tracking. Reusable across alerts, battery warnings, etc."""

from __future__ import annotations

import time
from collections.abc import Hashable


class RateLimiter:
    """Allow an action at most once per `cooldown_s` per key."""

    def __init__(self, cooldown_s: float) -> None:
        self._cooldown_s = cooldown_s
        self._last_fire: dict[Hashable, float] = {}

    def allow(self, key: Hashable, now_s: float | None = None) -> bool:
        timestamp = now_s if now_s is not None else time.monotonic()
        previous = self._last_fire.get(key)
        if previous is None or (timestamp - previous) >= self._cooldown_s:
            self._last_fire[key] = timestamp
            return True
        return False

    def reset(self, key: Hashable | None = None) -> None:
        if key is None:
            self._last_fire.clear()
        else:
            self._last_fire.pop(key, None)
