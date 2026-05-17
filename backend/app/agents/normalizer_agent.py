from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Dict, List

from backend.app.agents.agent_utils import _tokenize


def normalize_posts(posts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    normalized = []
    for post in posts:
        item = dict(post)
        item["text_clean"] = re.sub(r"https?://\S+", "", post["text"]).strip()
        item["tokens"] = sorted(_tokenize(item["text_clean"]))
        item["is_quote"] = "quotes" in post["text"].lower()
        item["is_repost"] = post["text"].lower().startswith("rt ")
        item["rumor_flag"] = any(token in post["text"].lower() for token in ["rumor", "unconfirmed", "reportedly", "据称", "传闻"])
        item["fetched_at"] = datetime.now(timezone.utc).isoformat()
        normalized.append(item)
    return normalized

__all__ = ["normalize_posts"]
