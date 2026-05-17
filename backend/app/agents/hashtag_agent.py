from __future__ import annotations

import re
from typing import Any, Dict, List

from backend.app.agents.agent_utils import _dedupe


def generate_hashtags(cluster: Dict[str, Any], trending_topics: List[Dict[str, Any]], language: str = "en") -> List[str]:
    zh_map = {
        "Bitcoin": "#\u6bd4\u7279\u5e01",
        "Ethereum": "#\u4ee5\u592a\u574a",
        "ETF": "#ETF",
        "Fed": "#\u7f8e\u8054\u50a8",
        "CPI": "#CPI",
        "Nvidia": "#\u82f1\u4f1f\u8fbe",
        "SEC": "#SEC",
        "Treasury": "#\u7f8e\u503a",
        "Oil": "#\u539f\u6cb9",
        "Gold": "#\u9ec4\u91d1",
    }
    tags = []
    for entity in cluster["entities"]:
        if language == "zh" and entity in zh_map:
            tags.append(zh_map[entity])
        else:
            clean = re.sub(r"[^A-Za-z0-9\u4e00-\u9fff]", "", entity)
            if clean:
                tags.append(f"#{clean}")
    industry = {
        "crypto_etf": "#\u52a0\u5bc6\u5e02\u573a" if language == "zh" else "#CryptoMarkets",
        "central_bank": "#\u5b8f\u89c2" if language == "zh" else "#Macro",
        "earnings": "#\u8d22\u62a5" if language == "zh" else "#Earnings",
        "regulation": "#\u76d1\u7ba1" if language == "zh" else "#Regulation",
        "macro_data": "#\u5b8f\u89c2\u6570\u636e" if language == "zh" else "#MacroData",
        "commodity": "#\u5927\u5b97\u5546\u54c1" if language == "zh" else "#Commodities",
        "market_move": "#\u5e02\u573a\u5feb\u8baf" if language == "zh" else "#MarketUpdate",
    }.get(cluster["event_type"], "#\u5e02\u573a\u5feb\u8baf" if language == "zh" else "#MarketUpdate")
    tags.append(industry)
    if language == "en":
        for topic in trending_topics:
            topic_value = topic["topic"]
            if len(tags) >= 5:
                break
            if topic_value not in tags and any(e.lower() in topic_value.lower() for e in cluster["entities"]):
                tags.append(topic_value)
    return _dedupe(tags)[:5] or (["#\u5e02\u573a\u5feb\u8baf", "#\u91d1\u878d"] if language == "zh" else ["#MarketUpdate", "#Finance", "#Markets"])


__all__ = ["generate_hashtags"]
