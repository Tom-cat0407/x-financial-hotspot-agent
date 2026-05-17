from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class XClient(ABC):
    @abstractmethod
    def fetch_posts_by_accounts(self, accounts: List[str]) -> List[Dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def fetch_posts_by_keywords(self, keywords: List[str]) -> List[Dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def fetch_trending_topics(self) -> List[Dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def fetch_post_metrics(self, post_id: str) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def upload_media(self, file_path: str) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def create_post(self, text: str, media_id: Optional[str] = None) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def get_publish_status(self, publish_id: str) -> Dict[str, Any]:
        raise NotImplementedError
