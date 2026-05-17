from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Dict, List

from sqlalchemy import delete, select

from backend.app.db.models import ArtifactRecord, EventCluster, PipelineState, RawPost, RunEvent
from backend.app.db.session import DatabaseSessionManager
from backend.app.services.memory_service import EMPTY_STATE, MemoryService


ARTIFACT_KEYS = {
    "hot_scores": "hot_score",
    "fact_checks": "fact_check",
    "generated_contents": "generated_content",
    "compliance_reports": "compliance_report",
    "image_cards": "image_card",
    "review_queue": "review_item",
    "publish_records": "publish_record",
    "platform_dispatches": "platform_dispatch",
    "performance_metrics": "performance_metric",
    "ab_test_variants": "ab_test_variant",
}


class DatabaseMemoryService(MemoryService):
    """PostgreSQL-backed memory with the same interface as JSON memory.

    A full state snapshot is retained for fast API reads, while key artifacts are
    also projected into queryable tables for production-style inspection.
    """

    def __init__(self, db: DatabaseSessionManager) -> None:
        self.db = db
        self.db.init_schema()
        super().__init__()
        with self.db.session() as session:
            row = session.get(PipelineState, "current")
            if row is None:
                session.add(PipelineState(key="current", payload=deepcopy(EMPTY_STATE)))

    def reset(self) -> Dict[str, Any]:
        state = deepcopy(EMPTY_STATE)
        self._write(state)
        return state

    def load(self) -> Dict[str, Any]:
        with self.db.session() as session:
            row = session.get(PipelineState, "current")
            if row is None:
                return self.reset()
            return deepcopy(row.payload)

    def _write(self, state: Dict[str, Any]) -> None:
        super()._write(state)
        with self.db.session() as session:
            row = session.get(PipelineState, "current")
            if row is None:
                session.add(PipelineState(key="current", payload=state))
            else:
                row.payload = state

    def save(self, key: str, records: List[Dict[str, Any]]) -> None:
        super().save(key, records)
        if key == "raw_posts":
            self._upsert_raw_posts(records)
        elif key == "event_clusters":
            self._upsert_event_clusters(records)
        elif key in ARTIFACT_KEYS:
            self._replace_artifacts(key, records)

    def replace_state(self, state: Dict[str, Any]) -> None:
        super().replace_state(state)
        if "raw_posts" in state:
            self._upsert_raw_posts(state.get("raw_posts", []))
        if "event_clusters" in state:
            self._upsert_event_clusters(state.get("event_clusters", []))
        for key in ARTIFACT_KEYS:
            if key in state:
                self._replace_artifacts(key, state.get(key, []))

    def log_event(self, state_name: str, message: str, payload: Dict[str, Any] | None = None) -> None:
        record = {
            "state": state_name,
            "message": message,
            "payload": payload or {},
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self.append("run_events", record)
        with self.db.session() as session:
            session.add(RunEvent(state=state_name, message=message, payload=payload or {}))

    def _upsert_raw_posts(self, records: List[Dict[str, Any]]) -> None:
        with self.db.session() as session:
            for record in records:
                row = session.get(RawPost, record["post_id"])
                if row is None:
                    session.add(
                        RawPost(
                            post_id=record["post_id"],
                            author_handle=record["author_handle"],
                            source_type=record["source_type"],
                            text=record["text"],
                            payload=record,
                            created_at=record["created_at"],
                            fetched_at=record.get("fetched_at", ""),
                        )
                    )
                else:
                    row.payload = record
                    row.fetched_at = record.get("fetched_at", "")

    def _upsert_event_clusters(self, records: List[Dict[str, Any]]) -> None:
        with self.db.session() as session:
            for record in records:
                row = session.get(EventCluster, record["cluster_id"])
                if row is None:
                    session.add(
                        EventCluster(
                            cluster_id=record["cluster_id"],
                            main_title=record["main_title"],
                            event_type=record["event_type"],
                            confidence_score=record.get("confidence_score", 0),
                            payload=record,
                        )
                    )
                else:
                    row.main_title = record["main_title"]
                    row.event_type = record["event_type"]
                    row.confidence_score = record.get("confidence_score", 0)
                    row.payload = record

    def _replace_artifacts(self, key: str, records: List[Dict[str, Any]]) -> None:
        record_type = ARTIFACT_KEYS[key]
        with self.db.session() as session:
            session.execute(delete(ArtifactRecord).where(ArtifactRecord.record_type == record_type))
            for record in records:
                external_id = (
                    record.get("content_id")
                    or record.get("cluster_id")
                    or record.get("publish_id")
                    or record.get("dispatch_id")
                    or record.get("variant_id")
                    or record.get("review_id")
                    or record.get("compliance_report_id")
                    or record_type
                )
                session.add(ArtifactRecord(record_type=record_type, external_id=str(external_id), payload=record))

            if key == "hot_scores":
                for record in records:
                    cluster = session.get(EventCluster, record["cluster_id"])
                    if cluster is not None:
                        cluster.hot_score = record.get("hot_score", 0)
