"""Push notification fan-out via Expo's hosted push service.

The mobile app registers its Expo push token with the RPi on first launch
(``POST /api/notifications/register``). When an event worth notifying about
fires — most importantly the user pressing SOS on the cane — this service
POSTs to Expo's push API, which then delivers via APNs / FCM to every
registered guardian phone.

We use Expo Push because:

- It works while the guardian's phone is locked or the app is backgrounded.
- It requires no Firebase setup for our test build (Expo handles it).
- It is a single HTTPS POST — no SDK, no persistent connection.

The RPi must have **internet access** for delivery to succeed. When offline,
the in-app polling path (``GET /api/status`` -> ``latest_alert``) still
shows the SOS while the app is in the foreground.
"""

from __future__ import annotations

import threading
from typing import Any

import httpx

from storage import GuardianDeviceRepository
from utils.logger import get_logger

EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"


class NotificationService:
    """Sends Expo push notifications to every registered guardian device."""

    def __init__(
        self,
        repository: GuardianDeviceRepository,
        client: httpx.Client | None = None,
        timeout_s: float = 5.0,
    ) -> None:
        self._repo = repository
        self._client = client if client is not None else httpx.Client(timeout=timeout_s)
        self._lock = threading.Lock()
        self._log = get_logger("services.notification")

    def register(
        self,
        push_token: str,
        label: str | None = None,
        platform: str | None = None,
    ) -> None:
        """Persist a phone's Expo push token. Upserts on repeated calls."""
        self._repo.save(push_token=push_token, label=label, platform=platform)
        self._log.info("registered guardian device label=%s platform=%s", label, platform)

    def send(
        self,
        title: str,
        body: str,
        data: dict[str, Any] | None = None,
        priority: str = "high",
        sound: str | None = "default",
    ) -> dict[str, Any]:
        """Fan out one notification to every registered token.

        Returns a summary dict with ``sent`` (count) and ``errors`` (list).
        Never raises — push failures are logged so the caller (e.g. the SOS
        service) is decoupled from network problems.
        """
        tokens = self._repo.all_tokens()
        if not tokens:
            self._log.warning("no guardian devices registered; %s not delivered", title)
            return {"sent": 0, "errors": ["no devices registered"]}

        messages = [
            {
                "to": token,
                "title": title,
                "body": body,
                "data": data or {},
                "priority": priority,
                "sound": sound,
            }
            for token in tokens
        ]

        try:
            with self._lock:
                response = self._client.post(
                    EXPO_PUSH_URL,
                    json=messages,
                    headers={
                        "Accept": "application/json",
                        "Accept-Encoding": "gzip, deflate",
                        "Content-Type": "application/json",
                    },
                )
            response.raise_for_status()
            payload = response.json()
            self._log.info(
                "expo push %s -> %d device(s); response=%s",
                title,
                len(tokens),
                payload,
            )
            return {"sent": len(tokens), "response": payload}
        except Exception as exc:
            self._log.warning("expo push failed: %s", exc)
            return {"sent": 0, "errors": [str(exc)]}

    def close(self) -> None:
        try:
            self._client.close()
        except Exception as exc:  # pragma: no cover
            self._log.debug("notification client close raised: %s", exc)
