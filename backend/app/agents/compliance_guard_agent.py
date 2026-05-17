from __future__ import annotations

import re
from typing import Any, Dict

from backend.app.agents.agent_utils import DEFAULT_BANNED_PATTERNS, _dedupe


def compliance_check(content: Dict[str, Any], fact_check: Dict[str, Any], llm_client: Any | None = None) -> Dict[str, Any]:
    text = content["tweet_text"].lower()
    issues = []
    for issue, patterns in DEFAULT_BANNED_PATTERNS.items():
        if any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns):
            issues.append(issue)
    if content.get("language") == "zh":
        if "\u4e0d\u6784\u6210\u6295\u8d44\u5efa\u8bae" not in content["tweet_text"]:
            issues.append("missing_disclaimer")
    elif "not investment advice" not in text:
        issues.append("missing_disclaimer")
    if fact_check["verification_status"] == "unverified" and any(token in text for token in ["confirmed", "proves", "official", "\u8bc1\u5b9e", "\u5b98\u65b9\u786e\u8ba4"]):
        issues.append("unverified_claim_presented_as_fact")

    llm_result: Dict[str, Any] = {}
    if llm_client is not None and getattr(llm_client, "enabled", False):
        llm_result = llm_client.review_compliance({"content": content, "fact_check": fact_check, "rule_issues": issues}) or {}
        issues = _dedupe(issues + llm_result.get("issues", []))

    if any(issue in issues for issue in ["investment_advice", "return_promise", "price_prediction"]):
        risk_level = "blocked"
    elif issues:
        risk_level = "high"
    elif fact_check["verification_status"] in {"unverified", "contradicted"}:
        risk_level = "medium"
    else:
        risk_level = llm_result.get("risk_level", "low")
    report = {
        "compliance_report_id": f"cmp_{content['content_id']}",
        "content_id": content["content_id"],
        "pass": risk_level in {"low", "medium"},
        "risk_level": risk_level,
        "issues": issues,
        "revision_instruction": llm_result.get("revision_instruction") or ("Remove risky wording and keep claims attributed." if issues else ""),
        "requires_human_review": True,
        "reviewed_by": "llm+rules" if llm_result else "rules",
    }
    if llm_client is not None and getattr(llm_client, "enabled", False) and not llm_result:
        report["llm_error"] = getattr(llm_client, "last_error", "unknown") or "empty_response"
    return report


__all__ = ["compliance_check"]
