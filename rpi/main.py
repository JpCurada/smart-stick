"""Entry point for the Smart Stick RPi backend.

Run with: `python -m rpi.main` (from the project root) or
`python main.py` (from inside the rpi/ directory).
"""

from __future__ import annotations

import sys
from pathlib import Path

import uvicorn


def _ensure_rpi_on_path() -> None:
    """Allow `python main.py` to resolve sibling packages."""
    rpi_dir = Path(__file__).resolve().parent
    if str(rpi_dir) not in sys.path:
        sys.path.insert(0, str(rpi_dir))


_ensure_rpi_on_path()

from api.app import create_app  # noqa: E402
from core.config import Config  # noqa: E402
from utils.logger import get_logger  # noqa: E402

log = get_logger("main")
app = create_app()


def main() -> None:
    log.info(
        "starting Smart Stick API on %s:%d (env=%s)",
        Config.API_HOST,
        Config.API_PORT,
        Config.ENVIRONMENT.value,
    )
    uvicorn.run(
        app,
        host=Config.API_HOST,
        port=Config.API_PORT,
        log_level=Config.LOG_LEVEL.lower(),
    )


if __name__ == "__main__":
    main()
