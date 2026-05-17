from __future__ import annotations

import json
import urllib.request
from typing import Any, Dict

from backend.app.core.config import settings


class AlertClient:
    def __init__(self, webhook_url: str = "", timeout_seconds: int = 5) -> None:
        self.webhook_url = webhook_url
        self.timeout_seconds = timeout_seconds
        self.enabled = bool(webhook_url)

    @classmethod
    def from_settings(cls) -> "AlertClient":
        return cls(webhook_url=settings.alert_webhook_url, timeout_seconds=settings.alert_timeout_seconds)

    def send(self, event_type: str, message: str, payload: Dict[str, Any] | None = None) -> Dict[str, Any]:
        if not self.enabled:
            return {"ok": False, "skipped": True, "reason": "alert_webhook_disabled"}
        body = json.dumps({"event_type": event_type, "message": message, "payload": payload or {}}, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            self.webhook_url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                return {"ok": 200 <= response.status < 300, "status_code": response.status, "skipped": False}
        except Exception as exc:
            return {"ok": False, "skipped": False, "error": str(exc)}


__all__ = ["AlertClient"]
