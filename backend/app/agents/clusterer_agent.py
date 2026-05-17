from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from backend.app.agents.agent_utils import _avg, _new_cluster, _post_cluster_similarity, _refresh_cluster


def cluster_posts(posts: List[Dict[str, Any]], similarity_threshold: float = 0.42) -> List[Dict[str, Any]]:
    clusters: List[Dict[str, Any]] = []
    for post in sorted(posts, key=lambda item: item["created_at"]):
        best_cluster: Optional[Dict[str, Any]] = None
        best_score = 0.0
        for cluster in clusters:
            score = _post_cluster_similarity(post, cluster)
            if score > best_score:
                best_score = score
                best_cluster = cluster
        if best_cluster is not None and best_score >= similarity_threshold:
            best_cluster["source_posts"].append(post)
            best_cluster["similarity_scores"].append(round(best_score, 3))
            _refresh_cluster(best_cluster)
        else:
            clusters.append(_new_cluster(post, len(clusters) + 1))

    for index, cluster in enumerate(clusters, start=1):
        cluster["cluster_id"] = f"evt_{datetime.now(timezone.utc).strftime('%Y%m%d')}_{index:03d}"
        cluster["source_post_ids"] = [p["post_id"] for p in cluster["source_posts"]]
        cluster["source_count"] = len(cluster["source_posts"])
        cluster["independent_source_count"] = len({p["author_handle"] for p in cluster["source_posts"]})
        cluster["confidence_score"] = round(
            min(0.55 + cluster["independent_source_count"] * 0.08 + len(cluster["entities"]) * 0.025 + _avg(cluster["similarity_scores"]) * 0.2, 0.96),
            2,
        )
    return clusters

__all__ = ["cluster_posts"]
