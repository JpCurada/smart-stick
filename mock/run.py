"""Entry point: starts the Smart Stick API server with fake sensor data.

Run from the repo root:
    python mock/run.py

The server binds to 0.0.0.0:5000 so any device on the same WiFi can reach
it. Point the mobile app at http://<your-laptop-ip>:5000.
"""
from __future__ import annotations

import socket
import sys
from pathlib import Path

# Ensure rpi/ is importable.
_RPI = Path(__file__).resolve().parent.parent / "rpi"
if str(_RPI) not in sys.path:
    sys.path.insert(0, str(_RPI))

# Also ensure mock/ itself is importable (for fake_sensors imports).
_MOCK = Path(__file__).resolve().parent.parent / "mock"
if str(_MOCK.parent) not in sys.path:
    sys.path.insert(0, str(_MOCK.parent))

import uvicorn  # noqa: E402

from api.app import create_app  # noqa: E402
from api.dependencies import set_container  # noqa: E402
from mock.mock_container import build_mock_container  # noqa: E402
from utils.logger import get_logger  # noqa: E402


def _local_ip() -> str:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"


if __name__ == "__main__":
    log = get_logger("mock.run")
    container = build_mock_container()
    set_container(container)
    app = create_app(container=container)

    host = "0.0.0.0"
    port = 5000
    local_ip = _local_ip()

    log.info("=" * 60)
    log.info("  Smart Stick MOCK server starting")
    log.info("  Local:   http://127.0.0.1:%d", port)
    log.info("  Network: http://%s:%d", local_ip, port)
    log.info("  Set EXPO_PUBLIC_API_BASE_URL=http://%s:%d in .env", local_ip, port)
    log.info("=" * 60)

    uvicorn.run(app, host=host, port=port, log_level="info")
