"""Compatibility exports for older imports.

The production pipeline imports each Agent module directly. This file remains
only as a stable facade for tests or external callers that used the earlier
single-module API.
"""

from backend.app.agents.agent_utils import (
    DEFAULT_BANNED_PATTERNS,
    ENTITY_PATTERNS,
    EVENT_RULES,
    STOPWORDS,
    write_report,
    _avg,
    _card_html,
    _centroid,
    _cluster_summary,
    _cluster_title,
    _content_record,
    _cosine,
    _dedupe,
    _font,
    _jaccard,
    _majority,
    _new_cluster,
    _post_cluster_similarity,
    _refresh_cluster,
    _render_html_card,
    _render_pillow_card,
    _text_vector,
    _tokenize,
    _within_time_window,
    _wrap,
)
from backend.app.agents.clusterer_agent import cluster_posts
from backend.app.agents.compliance_guard_agent import compliance_check
from backend.app.agents.emergency_priority_agent import classify_emergency
from backend.app.agents.entity_extractor_agent import extract_entities
from backend.app.agents.hashtag_agent import generate_hashtags
from backend.app.agents.image_card_agent import generate_image_card
from backend.app.agents.normalizer_agent import normalize_posts
from backend.app.agents.rag_fact_check_agent import fact_check_cluster
from backend.app.agents.tweet_generator_agent import generate_tweet


__all__ = [
    "DEFAULT_BANNED_PATTERNS",
    "ENTITY_PATTERNS",
    "EVENT_RULES",
    "STOPWORDS",
    "classify_emergency",
    "cluster_posts",
    "compliance_check",
    "extract_entities",
    "fact_check_cluster",
    "generate_hashtags",
    "generate_image_card",
    "generate_tweet",
    "normalize_posts",
    "write_report",
]
