from __future__ import annotations

from typing import Any, Dict, List, Optional

from backend.app.clients.x_client_base import XClient


class RealXClient(XClient):
    """Interface placeholder for real X API access.

    The demo intentionally keeps real publishing disabled unless credentials and
    explicit environment switches are provided. This preserves the ToS boundary
    required by the test while making the integration point clear.
    """

    def fetch_posts_by_accounts(self, accounts: List[str]) -> List[Dict[str, Any]]:
        raise NotImplementedError("Real X API credentials are not configured.")

    def fetch_posts_by_keywords(self, keywords: List[str]) -> List[Dict[str, Any]]:
        raise NotImplementedError("Real X API credentials are not configured.")

    def fetch_trending_topics(self) -> List[Dict[str, Any]]:
        raise NotImplementedError("Real X API credentials are not configured.")

    def fetch_post_metrics(self, post_id: str) -> Dict[str, Any]:
        raise NotImplementedError("Real X API credentials are not configured.")

    def upload_media(self, file_path: str) -> Dict[str, Any]:
        raise NotImplementedError("Real X API credentials are not configured.")

    def create_post(self, text: str, media_id: Optional[str] = None) -> Dict[str, Any]:
        raise NotImplementedError("Real X API credentials are not configured.")

    def get_publish_status(self, publish_id: str) -> Dict[str, Any]:
        raise NotImplementedError("Real X API credentials are not configured.")
