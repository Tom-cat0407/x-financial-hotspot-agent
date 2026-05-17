from __future__ import annotations

import re
from typing import Any, Dict, List

from backend.app.agents.agent_utils import _content_record


ZH_DISCLAIMER = "\u4e0d\u6784\u6210\u6295\u8d44\u5efa\u8bae\u3002"


def generate_tweet(
    cluster: Dict[str, Any],
    fact_check: Dict[str, Any],
    hashtags: List[str],
    style: str = "professional_news",
    language: str = "en",
    llm_client: Any | None = None,
) -> Dict[str, Any]:
    prompt_payload = {
        "style": style,
        "language": language,
        "cluster_title": cluster["main_title"],
        "summary": cluster["summary"],
        "entities": cluster["entities"],
        "event_type": cluster["event_type"],
        "verification_status": fact_check["verification_status"],
        "risk_note": fact_check.get("risk_note", ""),
        "hashtags": hashtags[:5],
        "constraints": [
            "280 characters or fewer",
            "original wording",
            "no investment advice",
            "no return promises",
            "no price predictions",
            "do not present unverified claims as confirmed facts",
        ],
    }
    if llm_client is not None and getattr(llm_client, "enabled", False):
        llm_text = llm_client.generate_tweet(prompt_payload)
        if llm_text:
            text = _fit_tweet(_ensure_hashtags(_ensure_disclaimer(llm_text.strip(), language), hashtags), language)
            return _content_record(cluster, style, language, text, hashtags, generated_by="llm")

    text = _fallback_tweet(cluster, fact_check, hashtags, style, language)
    record = _content_record(cluster, style, language, text, hashtags, generated_by="rules_fallback")
    if llm_client is not None and getattr(llm_client, "enabled", False):
        record["llm_error"] = getattr(llm_client, "last_error", "unknown") or "empty_response"
    return record


def _fallback_tweet(cluster: Dict[str, Any], fact_check: Dict[str, Any], hashtags: List[str], style: str, language: str) -> str:
    status_en = "supported by available mock evidence" if fact_check["verification_status"] in {"verified", "mostly_verified"} else "being discussed by market sources"
    status_zh = "\u5df2\u6709\u6a21\u62df\u6570\u636e\u652f\u6301" if fact_check["verification_status"] in {"verified", "mostly_verified"} else "\u4ecd\u5904\u4e8e\u5e02\u573a\u8ba8\u8bba\u9636\u6bb5"
    entity_text = ", ".join(cluster["entities"][:3]) or ("financial markets" if language == "en" else "\u91d1\u878d\u5e02\u573a")
    if language == "zh":
        prefix = {
            "professional_news": "\u5e02\u573a\u901f\u62a5\uff1a",
            "commentary": "\u5e02\u573a\u89c2\u5bdf\uff1a",
            "educational": "\u5feb\u901f\u79d1\u666e\uff1a",
        }.get(style, "\u5e02\u573a\u901f\u62a5\uff1a")
        event_label = {
            "crypto_etf": "\u52a0\u5bc6 ETF",
            "central_bank": "\u592e\u884c\u653f\u7b56",
            "earnings": "\u8d22\u62a5",
            "regulation": "\u76d1\u7ba1",
            "macro_data": "\u5b8f\u89c2\u6570\u636e",
            "commodity": "\u5927\u5b97\u5546\u54c1",
            "market_move": "\u5e02\u573a\u6ce2\u52a8",
        }.get(cluster["event_type"], "\u5e02\u573a")
        text = f"{prefix}{entity_text}{status_zh}\uff0c{cluster['source_count']} \u4e2a\u72ec\u7acb\u6a21\u62df\u6765\u6e90\u6b63\u5728\u5173\u6ce8\u8fd9\u4e00{event_label}\u4e8b\u4ef6\u3002 {ZH_DISCLAIMER}{' '.join(hashtags[:5])}"
    else:
        prefix = {"professional_news": "Market brief:", "commentary": "Market note:", "educational": "Quick explainer:"}.get(style, "Market brief:")
        text = f"{prefix} {entity_text} is {status_en}. {cluster['summary']} Not investment advice. {' '.join(hashtags[:5])}"
    return _fit_tweet(text, language)


def _ensure_disclaimer(text: str, language: str) -> str:
    if language == "zh":
        return text if "\u4e0d\u6784\u6210\u6295\u8d44\u5efa\u8bae" in text else f"{text} {ZH_DISCLAIMER}"
    return text if "not investment advice" in text.lower() else f"{text} Not investment advice."


def _ensure_hashtags(text: str, provided_hashtags: List[str]) -> str:
    existing = re.findall(r"#[A-Za-z0-9_\u4e00-\u9fff]+", text)
    normalized_existing = {tag.lower() for tag in existing}
    missing = [tag for tag in provided_hashtags[:5] if tag.lower() not in normalized_existing]
    if len(existing) >= 3:
        return text
    needed = max(0, 3 - len(existing))
    to_add = missing[:needed]
    return f"{text} {' '.join(to_add)}".strip() if to_add else text


def _fit_tweet(text: str, language: str = "en") -> str:
    if len(text) <= 280:
        return text
    disclaimer = f" {ZH_DISCLAIMER}" if language == "zh" else " Not investment advice."
    hashtags = " " + " ".join(re.findall(r"#[A-Za-z0-9_\u4e00-\u9fff]+", text)[-5:])
    budget = 280 - len(disclaimer) - len(hashtags) - 1
    core = re.sub(r"\s+#[A-Za-z0-9_\u4e00-\u9fff]+", "", text.replace(disclaimer.strip(), "")).strip()
    return core[: max(0, budget - 3)].rstrip() + "..." + disclaimer + hashtags


__all__ = ["generate_tweet"]
