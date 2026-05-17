from __future__ import annotations

from typing import Any, Dict


def classify_emergency(cluster: Dict[str, Any]) -> Dict[str, Any]:
    text = " ".join(p["text"].lower() for p in cluster["source_posts"])
    high = ["sec lawsuit", "bankruptcy", "exchange hack", "stablecoin depeg", "fed rate decision", "flash crash", "trading halt"]
    medium = ["cpi", "fomc", "earnings surprise", "rate hike", "rate cut", "doj investigation", "cftc action"]
    if any(token in text for token in high):
        return {
            "emergency_level": "high",
            "emergency_reason": "major financial event keyword detected",
            "emergency_boost": 15,
            "requires_human_review": True,
            "auto_publish_allowed": False,
        }
    if any(token in text for token in medium):
        return {
            "emergency_level": "medium",
            "emergency_reason": "macro, earnings, or regulatory event keyword detected",
            "emergency_boost": 10,
            "requires_human_review": True,
            "auto_publish_allowed": False,
        }
    return {
        "emergency_level": "low",
        "emergency_reason": "normal monitoring event",
        "emergency_boost": 0,
        "requires_human_review": True,
        "auto_publish_allowed": False,
    }


__all__ = ["classify_emergency"]
