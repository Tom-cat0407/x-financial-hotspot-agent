from __future__ import annotations

from typing import Any, Dict, List

from backend.app.clients.x_client_base import XClient
from backend.app.core.config_loader import load_accounts, load_keywords


def collect_posts(x_client: XClient, fallback_accounts: List[str], fallback_keywords: List[str]) -> Dict[str, Any]:
    accounts = load_accounts() or fallback_accounts
    keywords = load_keywords() or fallback_keywords
    account_posts = x_client.fetch_posts_by_accounts(accounts)
    keyword_posts = x_client.fetch_posts_by_keywords(keywords)
    trending_topics = x_client.fetch_trending_topics()
    return {
        "posts": account_posts + keyword_posts,
        "account_posts": account_posts,
        "keyword_posts": keyword_posts,
        "trending_topics": trending_topics,
        "accounts": accounts,
        "keywords": keywords,
    }
