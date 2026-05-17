from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any, Dict, List


SOURCE_AUTHORITY = {
    "media": 90,
    "official": 95,
    "kol": 70,
}

MARKET_KEYWORDS = {
    "fed",
    "cpi",
    "inflation",
    "rate",
    "bitcoin",
    "ethereum",
    "etf",
    "sec",
    "earnings",
    "guidance",
    "nvidia",
    "tesla",
    "liquidity",
}


def calculate_hot_score(cluster: Dict[str, Any], trending_topics: List[Dict[str, Any]]) -> Dict[str, Any]:
    posts = cluster["source_posts"]
    engagement_velocity = _engagement_velocity(posts, cluster["last_seen_at"])
    source_authority = min(20, sum(SOURCE_AUTHORITY.get(p["source_type"], 60) for p in posts) / max(len(posts), 1) / 5)
    cross_source_confirmation = min(15, cluster["independent_source_count"] * 4.5)
    text = " ".join(p["text"].lower() for p in posts)
    keyword_hits = {keyword for keyword in MARKET_KEYWORDS if keyword in text}
    entity_hits = {entity.lower() for entity in cluster.get("entities", []) if entity.lower() in MARKET_KEYWORDS}
    market_relevance = min(15, 5 + len(keyword_hits) * 1.7 + len(entity_hits) * 0.8)
    keyword_match = min(10, len(keyword_hits) * 1.2 + len(entity_hits) * 0.7)
    trend_boost = _trend_boost(text, trending_topics)
    time_decay = _time_decay(cluster["last_seen_at"])
    emergency_boost = cluster.get("emergency", {}).get("emergency_boost", 0)
    hot_score = engagement_velocity + source_authority + cross_source_confirmation + market_relevance + keyword_match + trend_boost + time_decay + emergency_boost
    return {
        "cluster_id": cluster["cluster_id"],
        "hot_score": round(min(hot_score, 100), 1),
        "score_breakdown": {
            "engagement_velocity": round(engagement_velocity, 1),
            "source_authority": round(source_authority, 1),
            "cross_source_confirmation": round(cross_source_confirmation, 1),
            "market_relevance": round(market_relevance, 1),
            "keyword_match": round(keyword_match, 1),
            "trend_boost": round(trend_boost, 1),
            "time_decay": round(time_decay, 1),
            "emergency_boost": round(emergency_boost, 1),
        },
    }


def _time_decay(last_seen_at: str) -> float:
    last_seen = datetime.fromisoformat(last_seen_at.replace("Z", "+00:00"))
    hours = max((datetime.now(timezone.utc) - last_seen).total_seconds() / 3600, 0)
    return 5 / (1 + hours / 2)


def _engagement_velocity(posts: List[Dict[str, Any]], fallback_seen_at: str) -> float:
    velocity = 0.0
    for post in posts:
        engagement = _weighted_engagement(post)
        age_hours = _age_hours(post.get("created_at") or fallback_seen_at)
        velocity += engagement / max(age_hours, 0.25)
    return min(30, math.log1p(velocity) * 4.2)


def _weighted_engagement(post: Dict[str, Any]) -> float:
    return (
        post.get("like_count", 0)
        + post.get("repost_count", 0) * 2
        + post.get("reply_count", 0) * 1.5
        + post.get("quote_count", 0) * 2
        + post.get("view_count", 0) * 0.004
    )


def _age_hours(timestamp: str) -> float:
    created_at = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    return max((datetime.now(timezone.utc) - created_at).total_seconds() / 3600, 0.25)


def _trend_boost(text: str, trending_topics: List[Dict[str, Any]]) -> float:
    boost = 0.0
    for topic in trending_topics:
        name = topic.get("topic", "").lower().lstrip("#")
        if name and name in text:
            volume = max(topic.get("volume", 0), 1)
            boost += min(2.5, math.log10(volume) - 2)
    return max(0.0, min(5.0, boost))
