from __future__ import annotations

import re
from typing import Any, Dict

from backend.app.agents.agent_utils import ENTITY_PATTERNS, EVENT_RULES, _text_vector
from backend.app.core.config import settings


VALID_EVENT_TYPES = set(EVENT_RULES) | {"market_move"}


def extract_entities(post: Dict[str, Any], llm_client: Any | None = None) -> Dict[str, Any]:
    text = post["text"]
    lowered = text.lower()
    entities = []
    for entity, patterns in ENTITY_PATTERNS.items():
        if any(re.search(pattern, lowered, flags=re.IGNORECASE) for pattern in patterns):
            entities.append(entity)
    for ticker in re.findall(r"\$?([A-Z]{2,5})(?:\b|$)", text):
        if ticker not in {"ETF", "CPI", "PPI", "SEC", "DOJ", "CFTC", "FOMC"} and ticker not in entities:
            entities.append(ticker)
    event_type = "market_move"
    for candidate, keywords in EVENT_RULES.items():
        if any(keyword in lowered for keyword in keywords):
            event_type = candidate
            break
    entity_types: Dict[str, str] = {}
    if settings.enable_llm_ner and llm_client is not None and getattr(llm_client, "enabled", False):
        llm_result = llm_client.extract_financial_entities({"text": text, "author": post.get("author_handle", ""), "lang": post.get("lang", "en")}) or {}
        for entity in llm_result.get("entities", []):
            if entity not in entities:
                entities.append(entity)
        llm_event_type = llm_result.get("event_type")
        if llm_event_type in VALID_EVENT_TYPES:
            event_type = llm_event_type
        entity_types = {str(key): str(value) for key, value in llm_result.get("entity_types", {}).items()}
    enriched = dict(post)
    enriched["entities"] = entities
    enriched["entity_types"] = entity_types
    enriched["event_type"] = event_type
    enriched["semantic_vector"] = _text_vector(post["text_clean"])
    return enriched

__all__ = ["extract_entities"]
