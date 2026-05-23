"""Watch the ESP32 telemetry packet for the SOS flag and fan out alerts.

The ESP32 firmware sets ``sos_active = 1`` in its SPI packet when the cane
user holds the physical SOS button. This service polls the telemetry
sensor on a background thread, detects the **rising edge** of that flag
(false -> true), and dispatches one push notification per press.

The notification payload includes:

- timestamp of the press
- current GPS lat / lng (or "unknown" if no fix yet)
- a Google Maps deep link the guardian can tap
- an in-app deep link (``smartstick://location``) to jump to the live view

The push is decoupled from the SPI poll loop so any HTTPS slowness never
delays the next telemetry read.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

from sensors import StickTelemetrySensor
from services.notification_service import NotificationService
from utils.logger import get_logger

# Minimum gap between two consecutive SOS pushes. The ESP32 button is a
# toggle (2s hold), but if the user double-presses we still send at most
# one push per this window — keeps the guardian's lock screen sane.
_DEFAULT_COOLDOWN_S = 10.0

# How often the watcher polls the telemetry sensor.
_DEFAULT_POLL_INTERVAL_S = 0.5


LocationGetter = Callable[[], dict[str, Any] | None]


class SosService:
    """Background watcher that fires push notifications on SOS rising edges."""

    def __init__(
        self,
        telemetry: StickTelemetrySensor,
        notifications: NotificationService,
        location_getter: LocationGetter,
        cooldown_s: float = _DEFAULT_COOLDOWN_S,
        poll_interval_s: float = _DEFAULT_POLL_INTERVAL_S,
    ) -> None:
        self._telemetry = telemetry
        self._notifications = notifications
        self._location_getter = location_getter
        self._cooldown_s = cooldown_s
        self._poll_interval_s = poll_interval_s
        self._stop_flag = threading.Event()
        self._thread: threading.Thread | None = None
        self._last_sos_state = False
        self._last_fired_at = 0.0
        self._latest_event: dict[str, Any] | None = None
        self._lock = threading.Lock()
        self._log = get_logger("services.sos")

    def latest_event(self) -> dict[str, Any] | None:
        """Most recent SOS event payload (or None). Used by /api/status."""
        with self._lock:
            return dict(self._latest_event) if self._latest_event else None

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_flag.clear()
        self._thread = threading.Thread(target=self._run, name="sos-watcher", daemon=True)
        self._thread.start()
        self._log.info("sos watcher started")

    def stop(self, timeout_s: float = 2.0) -> None:
        self._stop_flag.set()
        if self._thread is not None:
            self._thread.join(timeout=timeout_s)
            self._thread = None

    def fire_test(self) -> dict[str, Any]:
        """Send a dummy SOS without needing the physical button. For QA."""
        return self._fire(reason="test")

    def _run(self) -> None:
        while not self._stop_flag.is_set():
            try:
                reading = self._telemetry.read()
                if reading.healthy:
                    sos_now = bool(reading.data.get("sos_active"))
                    if sos_now and not self._last_sos_state:
                        self._fire(reason="button")
                    self._last_sos_state = sos_now
            except Exception as exc:
                self._log.debug("sos watcher poll error: %s", exc)
            time.sleep(self._poll_interval_s)

    def _fire(self, reason: str) -> dict[str, Any]:
        now = time.monotonic()
        if now - self._last_fired_at < self._cooldown_s:
            self._log.debug("sos fire suppressed (cooldown)")
            return {"sent": 0, "suppressed": True}
        self._last_fired_at = now

        ts = datetime.now(timezone.utc)
        location = self._location_getter() or {}
        lat = location.get("latitude")
        lng = location.get("longitude")

        if lat is not None and lng is not None:
            maps_url = f"https://maps.google.com/?q={lat:.6f},{lng:.6f}"
            location_line = f"{lat:.5f}, {lng:.5f}"
        else:
            maps_url = None
            location_line = "Unknown (no GPS fix yet)"

        body = f"Time: {ts.strftime('%H:%M:%S')}\nLocation: {location_line}"
        data = {
            "type": "sos",
            "trigger": reason,
            "timestamp": ts.isoformat(),
            "latitude": lat,
            "longitude": lng,
            "maps_url": maps_url,
            "deep_link": "smartstick://location",
        }

        self._log.warning("SOS fired (reason=%s) — notifying guardians", reason)
        with self._lock:
            self._latest_event = dict(data)
        return self._notifications.send(title="Emergency SOS", body=body, data=data)
