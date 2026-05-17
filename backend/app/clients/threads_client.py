from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict

from backend.app.core.config import settings


class ThreadsClient:
    """Threads distribution adapter.

    The default implementation is a mock adapter because public Threads posting
    requires account-specific credentials and review. The interface mirrors a
    real adapter so the pipeline can distribute without changing orchestration.
    """

    def __init__(self, enabled: bool = False, mode: str = "mock") -> None:
        self.enabled = enabled
        self.mode = mode
        self._counter = 0

    @classmethod
    def from_settings(cls) -> "ThreadsClient":
        return cls(enabled=settings.threads_enabled, mode=settings.threads_mode)

    def publish(self, text: str, source_url: str = "") -> Dict[str, Any]:
        if not self.enabled:
            return {"ok": False, "skipped": True, "platform": "threads", "reason": "threads_disabled"}
        self._counter += 1
        post_id = f"mock_threads_{self._counter:03d}"
        return {
            "ok": True,
            "skipped": False,
            "platform": "threads",
            "mode": self.mode,
            "threads_post_id": post_id,
            "threads_post_url": f"mock://threads/{post_id}",
            "source_url": source_url,
            "published_at": datetime.now(timezone.utc).isoformat(),
        }
