"""Pytest fixtures shared across the test suite.

Every fixture here is hardware-free: sensors are mocked, the database is
created in a temporary directory, and the YOLO model is never loaded.
"""

from __future__ import annotations

import sys
from collections.abc import Iterator
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Ensure rpi/ is on sys.path so `import core`, `import sensors`, etc. resolve.
_RPI_DIR = Path(__file__).resolve().parent.parent
if str(_RPI_DIR) not in sys.path:
    sys.path.insert(0, str(_RPI_DIR))


@pytest.fixture
def database(tmp_path: Path) -> Iterator:
    """Fresh per-test database in a temp directory."""
    from storage.database import Database
    from storage.migrations import run_migrations

    db = Database(path=tmp_path / "test.db")
    run_migrations(db)
    yield db
    db.close()


@pytest.fixture
def mock_bridge() -> MagicMock:
    bridge = MagicMock()
    bridge.is_healthy.return_value = True
    bridge.send_vibration.return_value = True
    bridge.send_buzz.return_value = True
    bridge.request_battery_status.return_value = {
        "voltage_v": 4.0,
        "current_ma": 2000,
        "percentage": 75,
        "temperature_c": 35.0,
    }
    return bridge


@pytest.fixture
def mock_camera() -> MagicMock:
    """A camera that returns a deterministic frame payload."""
    try:
        import numpy as np

        frame = np.zeros((480, 640, 3), dtype=np.uint8)
    except ImportError:
        frame = [[0] * 640 for _ in range(480)]

    reading = MagicMock()
    reading.healthy = True
    reading.data = {"frame": frame, "width": 640, "height": 480}

    camera = MagicMock()
    camera.read.return_value = reading
    camera.is_healthy.return_value = True
    return camera


@pytest.fixture
def mock_gps() -> MagicMock:
    reading = MagicMock()
    reading.healthy = True
    reading.data = {
        "latitude": 14.5995,
        "longitude": 120.9842,
        "altitude": 12.0,
        "accuracy_m": 5.0,
        "speed": 1.0,
        "fix_quality": 1,
    }
    from utils.converters import now_utc

    reading.timestamp = now_utc()

    gps = MagicMock()
    gps.read.return_value = reading
    return gps
