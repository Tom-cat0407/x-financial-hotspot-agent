from __future__ import annotations

import json
import hashlib
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.app.clients.x_client_base import XClient
from backend.app.core.config import DATA_DIR, settings


class MockXRateLimitError(RuntimeError):
    def __init__(self, endpoint: str, reset_time: str) -> None:
        super().__init__(f"Mock rate limit reached for {endpoint}; reset at {reset_time}")
        self.endpoint = endpoint
        self.reset_time = reset_time


class MockXClient(XClient):
    def __init__(self, data_dir: Path = DATA_DIR) -> None:
        self.data_dir = data_dir
        self._published: Dict[str, Dict[str, Any]] = {}
        self._created_texts: set[str] = set()
        self._rate_limits: Dict[str, Dict[str, Any]] = {}

    def fetch_posts_by_accounts(self, accounts: List[str]) -> List[Dict[str, Any]]:
        self._consume("fetch_posts_by_accounts", limit=100)
        posts = self._load_json("mock_x_posts.json")
        if not accounts:
            return posts
        account_set = {a.lower().lstrip("@") for a in accounts}
        return [p for p in posts if p["author_handle"].lower().lstrip("@") in account_set]

    def fetch_posts_by_keywords(self, keywords: List[str]) -> List[Dict[str, Any]]:
        self._consume("fetch_posts_by_keywords", limit=100)
        posts = self._load_json("mock_x_posts.json")
        lowered = [k.lower() for k in keywords]
        return [p for p in posts if any(k in p["text"].lower() for k in lowered)]

    def fetch_trending_topics(self) -> List[Dict[str, Any]]:
        self._consume("fetch_trending_topics", limit=30)
        return self._load_json("mock_trending_topics.json")

    def fetch_post_metrics(self, post_id: str) -> Dict[str, Any]:
        self._consume("fetch_post_metrics", limit=200)
        if post_id in self._published:
            record = self._published[post_id]
            seed = _stable_seed(record["tweet_text"])
            age_bucket = _age_bucket(record.get("published_at", ""))
            quality = 1 + seed % 9
            view_count = 1200 + (seed % 120) * 43 + age_bucket * 240
            like_count = 14 + quality * 5 + age_bucket * 4
            repost_count = 4 + quality * 2 + age_bucket
            reply_count = 3 + seed % 9 + max(1, age_bucket // 2)
            quote_count = 1 + seed % 6 + max(0, age_bucket // 3)
            return {
                "post_id": post_id,
                "like_count": like_count,
                "repost_count": repost_count,
                "reply_count": reply_count,
                "quote_count": quote_count,
                "view_count": view_count,
            }
        posts = self._load_json("mock_x_posts.json")
        post = next((p for p in posts if p["post_id"] == post_id), None)
        if not post:
            return {"post_id": post_id, "like_count": 0, "repost_count": 0, "reply_count": 0, "quote_count": 0, "view_count": 0}
        seed = _stable_seed(post["text"])
        age_bucket = _age_bucket(post.get("created_at", ""))
        growth = (seed % 11) + min(age_bucket, 18)
        return {
            "post_id": post_id,
            "like_count": post["like_count"] + growth,
            "repost_count": post["repost_count"] + max(1, growth // 3),
            "reply_count": post["reply_count"] + max(1, growth // 4),
            "quote_count": post["quote_count"] + max(0, growth // 5),
            "view_count": post["view_count"] + growth * 128,
        }

    def upload_media(self, file_path: str) -> Dict[str, Any]:
        self._consume("upload_media", limit=50)
        media_id = f"mock_media_{abs(hash(file_path)) % 100000}"
        return {"media_id": media_id, "file_path": file_path, "status": "uploaded"}

    def create_post(self, text: str, media_id: Optional[str] = None) -> Dict[str, Any]:
        self._consume("create_post", limit=20)
        normalized = " ".join(text.split()).lower()
        if normalized in self._created_texts:
            return {"ok": False, "status_code": 409, "error": "duplicate_content"}
        if "force_publish_failure" in normalized:
            return {"ok": False, "status_code": 500, "error": "mock_publish_failure"}

        self._created_texts.add(normalized)
        mock_post_id = f"mock_post_{len(self._published) + 1:03d}"
        publish_id = f"pub_mock_{len(self._published) + 1:03d}"
        url = f"{settings.public_base_url}/mock_x/posts/{mock_post_id}"
        record = {
            "ok": True,
            "status_code": 200,
            "publish_id": publish_id,
            "mock_post_id": mock_post_id,
            "mock_post_url": url,
            "tweet_text": text,
            "media_id": media_id,
            "published_at": datetime.now(timezone.utc).isoformat(),
        }
        self._published[mock_post_id] = record
        return record

    def get_publish_status(self, publish_id: str) -> Dict[str, Any]:
        for record in self._published.values():
            if record["publish_id"] == publish_id:
                return {"publish_id": publish_id, "status": "published", "record": record}
        return {"publish_id": publish_id, "status": "unknown"}

    def get_mock_post(self, mock_post_id: str) -> Optional[Dict[str, Any]]:
        return self._published.get(mock_post_id)

    def reset_publications(self) -> None:
        self._published = {}
        self._created_texts = set()

    def simulate_429(self, endpoint: str = "create_post") -> Dict[str, Any]:
        reset_time = (datetime.now(timezone.utc) + timedelta(seconds=30)).isoformat()
        self._rate_limits[endpoint] = {"remaining": 0, "reset_time": reset_time}
        return {"endpoint": endpoint, "status_code": 429, "reset_time": reset_time}

    def _consume(self, endpoint: str, limit: int) -> None:
        now = datetime.now(timezone.utc)
        state = self._rate_limits.setdefault(
            endpoint,
            {"remaining": limit, "reset_time": (now + timedelta(minutes=15)).isoformat()},
        )
        reset_time = datetime.fromisoformat(state["reset_time"])
        if now >= reset_time:
            state["remaining"] = limit
            state["reset_time"] = (now + timedelta(minutes=15)).isoformat()
        if state["remaining"] <= 0:
            raise MockXRateLimitError(endpoint, state["reset_time"])
        state["remaining"] -= 1

    def _load_json(self, name: str) -> List[Dict[str, Any]]:
        with (self.data_dir / name).open("r", encoding="utf-8") as f:
            return json.load(f)


def _stable_seed(value: str) -> int:
    return int(hashlib.sha256(value.encode("utf-8")).hexdigest()[:8], 16)


def _age_bucket(timestamp: str) -> int:
    try:
        created_at = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError:
        return 0
    age_seconds = max(0, int((datetime.now(timezone.utc) - created_at).total_seconds()))
    return min(24, age_seconds // 60)
