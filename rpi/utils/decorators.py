"""Reusable decorators."""

from __future__ import annotations

import functools
import time
from collections.abc import Callable
from typing import Any, TypeVar

from utils.logger import get_logger

F = TypeVar("F", bound=Callable[..., Any])

_log = get_logger(__name__)


def timed(func: F) -> F:
    """Log how long a function takes to execute."""

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        start = time.perf_counter()
        try:
            return func(*args, **kwargs)
        finally:
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            _log.debug("%s took %.2f ms", func.__qualname__, elapsed_ms)

    return wrapper  # type: ignore[return-value]


def retry(
    attempts: int = 3,
    delay_s: float = 0.1,
    exceptions: tuple[type[BaseException], ...] = (Exception,),
) -> Callable[[F], F]:
    """Retry a callable up to `attempts` times on the given exceptions."""

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exc: BaseException | None = None
            for attempt in range(1, attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as exc:
                    last_exc = exc
                    if attempt == attempts:
                        break
                    _log.warning(
                        "%s failed (attempt %d/%d): %s",
                        func.__qualname__,
                        attempt,
                        attempts,
                        exc,
                    )
                    time.sleep(delay_s)
            assert last_exc is not None
            raise last_exc

        return wrapper  # type: ignore[return-value]

    return decorator
