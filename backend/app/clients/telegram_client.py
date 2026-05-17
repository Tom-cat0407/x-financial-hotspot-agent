from __future__ import annotations

import json
import urllib.parse
import urllib.request
from typing import Any, Dict

from backend.app.core.config import settings


class TelegramClient:
    def __init__(
        self,
        enabled: bool = False,
        bot_token: str = "",
        chat_id: str = "",
        timeout_seconds: int = 10,
    ) -> None:
        self.enabled = enabled
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.timeout_seconds = timeout_seconds

    @classmethod
    def from_settings(cls) -> "TelegramClient":
        return cls(
            enabled=settings.telegram_enabled,
            bot_token=settings.telegram_bot_token,
            chat_id=settings.telegram_chat_id,
            timeout_seconds=settings.telegram_timeout_seconds,
        )

    def publish(self, text: str, source_url: str = "") -> Dict[str, Any]:
        if not self.enabled:
            return {"ok": False, "skipped": True, "platform": "telegram", "reason": "telegram_disabled"}
        if not self.bot_token or not self.chat_id:
            return {"ok": False, "skipped": True, "platform": "telegram", "reason": "telegram_credentials_missing"}

        payload = {
            "chat_id": self.chat_id,
            "text": f"{text}\n\nSource: {source_url}" if source_url else text,
            "disable_web_page_preview": False,
        }
        data = urllib.parse.urlencode(payload).encode("utf-8")
        request = urllib.request.Request(
            f"https://api.telegram.org/bot{self.bot_token}/sendMessage",
            data=data,
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                body = json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            return {"ok": False, "skipped": False, "platform": "telegram", "error": str(exc)}

        message = body.get("result", {})
        return {
            "ok": bool(body.get("ok")),
            "skipped": False,
            "platform": "telegram",
            "telegram_message_id": message.get("message_id"),
            "chat_id": self.chat_id,
        }
