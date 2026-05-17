from __future__ import annotations

import json
from typing import Any, Dict

from backend.app.core.config import DATA_DIR


def fact_check_cluster(cluster: Dict[str, Any], finance_client: Any | None = None) -> Dict[str, Any]:
    entities = cluster["entities"]
    if finance_client is not None:
        market_data = finance_client.lookup_entities(entities)
    else:
        with (DATA_DIR / "mock_market_data.json").open("r", encoding="utf-8") as f:
            market_data = json.load(f)
    evidence = []
    status = "partially_verified"
    for entity in entities:
        if entity in market_data:
            value = market_data[entity]
            if isinstance(value, list):
                for item in value:
                    evidence.append({"source": item.get("source", "finance_data"), "field": entity, "value": item})
            elif isinstance(value, dict):
                evidence.append({"source": value.get("source", "finance_data"), "field": entity, "value": value})
            else:
                evidence.append({"source": "mock_market_data", "field": entity, "value": value})
    if cluster["independent_source_count"] >= 3 and evidence:
        status = "mostly_verified"
    if cluster["event_type"] in {"central_bank", "earnings", "macro_data"} and evidence:
        status = "verified"
    if not evidence:
        status = "unverified"
    if any(p.get("rumor_flag") for p in cluster["source_posts"]) and status == "verified":
        status = "mostly_verified"
    return {
        "cluster_id": cluster["cluster_id"],
        "claim": cluster["summary"],
        "verification_status": status,
        "evidence_sources": evidence,
        "risk_note": "X posts are early signals; mock market data and source diversity determine demo verification status.",
    }

__all__ = ["fact_check_cluster"]
