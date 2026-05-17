from __future__ import annotations

import json
import math
import re
from datetime import datetime
from typing import Any, Dict, Iterable, List, Sequence, Set

from backend.app.agents.card_utils import CARDS_DIR, _card_html, _font, _render_html_card, _render_pillow_card, _wrap
from backend.app.core.config import REPORTS_DIR


STOPWORDS = {
    "the", "a", "an", "and", "or", "to", "of", "in", "as", "for", "on", "with",
    "from", "is", "are", "by", "that", "this", "it", "into", "about", "watch",
    "focus", "market", "markets",
}

ENTITY_PATTERNS = {
    "Bitcoin": [r"\bbitcoin\b", r"\bbtc\b"],
    "Ethereum": [r"\bethereum\b", r"\beth\b"],
    "ETF": [r"\betf\b", r"\betfs\b"],
    "Fed": [r"\bfed\b", r"\bfomc\b", r"federal reserve"],
    "CPI": [r"\bcpi\b", r"inflation"],
    "PPI": [r"\bppi\b"],
    "Nvidia": [r"\bnvidia\b", r"\bnvda\b"],
    "Tesla": [r"\btesla\b", r"\btsla\b"],
    "Apple": [r"\bapple\b", r"\baapl\b"],
    "Microsoft": [r"\bmicrosoft\b", r"\bmsft\b"],
    "SEC": [r"\bsec\b"],
    "CFTC": [r"\bcftc\b"],
    "DOJ": [r"\bdoj\b"],
    "Treasury": [r"\btreasury\b", r"\byield\b", r"\byields\b"],
    "Oil": [r"\boil\b", r"\bbrent\b", r"\bwti\b"],
    "Gold": [r"\bgold\b"],
}

EVENT_RULES = {
    "crypto_etf": ["bitcoin", "btc", "ethereum", "eth", "etf", "inflow", "outflow"],
    "central_bank": ["fed", "fomc", "rate", "inflation", "cpi", "ppi", "powell", "central bank"],
    "earnings": ["earnings", "guidance", "revenue", "margin", "nvidia", "nvda", "tesla", "aapl", "msft"],
    "regulation": ["sec", "cftc", "doj", "lawsuit", "approval", "regulator", "compliance"],
    "macro_data": ["jobs", "payrolls", "gdp", "unemployment", "yield", "treasury"],
    "commodity": ["oil", "gold", "brent", "wti", "opec"],
    "market_move": ["rally", "selloff", "flash crash", "trading halt", "liquidity"],
}

DEFAULT_BANNED_PATTERNS = {
    "investment_advice": [
        r"\bbuy now\b", r"\bsell now\b", r"\bstrong buy\b", r"\bmust invest\b",
        "\u7a33\u8d5a", "\u5fc5\u6da8", "\u6284\u5e95", "\u68ad\u54c8",
        "\u9a6c\u4e0a\u4e70\u5165", "\u9a6c\u4e0a\u5356\u51fa",
    ],
    "return_promise": [
        r"\bguaranteed return\b", r"\brisk free\b", r"\b100 percent profit\b",
        "\u7a33\u8d5a\u4e0d\u8d54", "\u65e0\u98ce\u9669\u6536\u76ca",
    ],
    "hype": [
        "\u53f2\u8bd7\u7ea7\u673a\u4f1a", "\u9519\u8fc7\u5c31\u6ca1\u4e86",
        "\u5fc5\u7136\u66b4\u6da8", "\u7edd\u5bf9\u786e\u5b9a",
        "\u5386\u53f2\u6027\u66b4\u5bcc\u673a\u4f1a",
    ],
    "price_prediction": [r"\bwill hit\s+\d+", r"\bto\s+\$\d+", "\u4e00\u5b9a\u5230"],
}


def write_report(report: Dict[str, Any]) -> str:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    path = REPORTS_DIR / f"{report['compliance_report_id']}.json"
    with path.open("w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    return str(path)


def _new_cluster(post: Dict[str, Any], index: int) -> Dict[str, Any]:
    cluster = {"cluster_id": f"tmp_{index}", "source_posts": [post], "similarity_scores": [1.0]}
    _refresh_cluster(cluster)
    return cluster


def _refresh_cluster(cluster: Dict[str, Any]) -> None:
    posts = cluster["source_posts"]
    entities = sorted({entity for post in posts for entity in post.get("entities", [])})
    event_type = _majority([p.get("event_type", "market_move") for p in posts])
    cluster.update(
        {
            "main_title": _cluster_title(event_type, entities, posts[0]["text_clean"]),
            "summary": _cluster_summary(event_type, entities, len(posts)),
            "entities": entities,
            "event_type": event_type,
            "first_seen_at": min(p["created_at"] for p in posts),
            "last_seen_at": max(p["created_at"] for p in posts),
            "centroid_tokens": sorted(set().union(*[set(p.get("tokens", [])) for p in posts])),
            "centroid_vector": _centroid([p.get("semantic_vector", []) for p in posts]),
        }
    )


def _post_cluster_similarity(post: Dict[str, Any], cluster: Dict[str, Any]) -> float:
    if not _within_time_window(post["created_at"], cluster["last_seen_at"], hours=6):
        return 0.0
    entity_score = _jaccard(set(post.get("entities", [])), set(cluster.get("entities", [])))
    token_score = _jaccard(set(post.get("tokens", [])), set(cluster.get("centroid_tokens", [])))
    vector_score = _cosine(post.get("semantic_vector", []), cluster.get("centroid_vector", []))
    type_score = 1.0 if post.get("event_type") == cluster.get("event_type") else 0.25
    return 0.35 * entity_score + 0.25 * token_score + 0.25 * vector_score + 0.15 * type_score


def _cluster_title(event_type: str, entities: List[str], sample_text: str) -> str:
    entity_text = ", ".join(entities[:3]) if entities else "Markets"
    titles = {
        "crypto_etf": f"{entity_text} ETF and crypto flow discussion gains attention",
        "central_bank": f"{entity_text} macro policy signals move into focus",
        "earnings": f"{entity_text} earnings and guidance draw investor attention",
        "regulation": f"{entity_text} regulatory development becomes a hotspot",
        "macro_data": f"{entity_text} macro data and yields drive discussion",
        "commodity": f"{entity_text} commodity move enters market focus",
        "market_move": f"{entity_text} market move draws discussion",
    }
    return titles.get(event_type, sample_text[:90])


def _cluster_summary(event_type: str, entities: List[str], source_count: int) -> str:
    entity_text = ", ".join(entities[:3]) if entities else "the topic"
    return f"{source_count} independent mock sources are discussing {entity_text} in a {event_type.replace('_', ' ')} context."


def _content_record(cluster: Dict[str, Any], style: str, language: str, text: str, hashtags: List[str], generated_by: str) -> Dict[str, Any]:
    return {
        "content_id": f"cnt_{cluster['cluster_id']}_{language}",
        "cluster_id": cluster["cluster_id"],
        "style": style,
        "language": language,
        "tweet_text": text,
        "char_count": len(text),
        "hashtags": hashtags[:5],
        "source_cluster_id": cluster["cluster_id"],
        "generated_by": generated_by,
    }


def _tokenize(text: str) -> Set[str]:
    tokens = {token.lower() for token in re.findall(r"[A-Za-z][A-Za-z0-9$]{1,}|[\u4e00-\u9fff]{2,}", text)}
    return {token.strip("$") for token in tokens if token.lower() not in STOPWORDS and len(token) > 1}


def _text_vector(text: str, dims: int = 48) -> List[float]:
    vector = [0.0] * dims
    for token in _tokenize(text):
        vector[abs(hash(token)) % dims] += 1.0
    norm = math.sqrt(sum(value * value for value in vector)) or 1.0
    return [round(value / norm, 6) for value in vector]


def _centroid(vectors: Sequence[Sequence[float]]) -> List[float]:
    vectors = [v for v in vectors if v]
    if not vectors:
        return []
    dims = len(vectors[0])
    centroid = [sum(vector[index] for vector in vectors) / len(vectors) for index in range(dims)]
    norm = math.sqrt(sum(value * value for value in centroid)) or 1.0
    return [round(value / norm, 6) for value in centroid]


def _cosine(left: Sequence[float], right: Sequence[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    return max(0.0, min(1.0, sum(a * b for a, b in zip(left, right))))


def _jaccard(left: Set[str], right: Set[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def _within_time_window(left: str, right: str, hours: int) -> bool:
    left_dt = datetime.fromisoformat(left.replace("Z", "+00:00"))
    right_dt = datetime.fromisoformat(right.replace("Z", "+00:00"))
    return abs((left_dt - right_dt).total_seconds()) <= hours * 3600


def _avg(values: Sequence[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _majority(values: Iterable[str]) -> str:
    counts: Dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return max(counts.items(), key=lambda item: item[1])[0]


def _dedupe(values: Sequence[str]) -> List[str]:
    result = []
    for value in values:
        if value and value not in result:
            result.append(value)
    return result

