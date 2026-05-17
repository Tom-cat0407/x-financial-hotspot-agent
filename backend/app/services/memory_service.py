from __future__ import annotations

import json
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from typing import Any, Dict, List

from backend.app.core.config import OUTPUTS_DIR, STATE_FILE

try:
    from filelock import FileLock
except ImportError:  # pragma: no cover - optional dependency fallback
    FileLock = None  # type: ignore[assignment]


EMPTY_STATE: Dict[str, Any] = {
    "raw_posts": [],
    "event_clusters": [],
    "hot_scores": [],
    "fact_checks": [],
    "generated_contents": [],
    "compliance_reports": [],
    "image_cards": [],
    "review_queue": [],
    "publish_records": [],
    "platform_dispatches": [],
    "performance_metrics": [],
    "ab_test_variants": [],
    "strategy_memory": {
        "source_weight": {},
        "style_weight": {"professional_news": 1.0, "commentary": 1.0, "educational": 1.0},
        "hashtag_weight": {},
    },
    "run_events": [],
}


class MemoryService:
    def __init__(self, state_file: Path = STATE_FILE) -> None:
        self.state_file = state_file
        self._thread_lock = RLock()
        self._file_lock = FileLock(str(self.state_file) + ".lock") if FileLock else None
        OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
        if not self.state_file.exists():
            self.reset()

    def reset(self) -> Dict[str, Any]:
        with self._locked():
            state = deepcopy(EMPTY_STATE)
            self._write(state)
            return state

    def load(self) -> Dict[str, Any]:
        with self._locked():
            return self._load_unlocked()

    def save(self, key: str, records: List[Dict[str, Any]]) -> None:
        with self._locked():
            state = self._load_unlocked()
            state[key] = records
            self._write(state)

    def append(self, key: str, record: Dict[str, Any]) -> None:
        with self._locked():
            state = self._load_unlocked()
            state.setdefault(key, []).append(record)
            self._write(state)

    def replace_state(self, state: Dict[str, Any]) -> None:
        with self._locked():
            self._write(state)

    def log_event(self, state_name: str, message: str, payload: Dict[str, Any] | None = None) -> None:
        self.append(
            "run_events",
            {
                "state": state_name,
                "message": message,
                "payload": payload or {},
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
        )

    def update_strategy_after_publish(
        self,
        publish_records: List[Dict[str, Any]],
        performance_metrics: List[Dict[str, Any]] | None = None,
    ) -> None:
        with self._locked():
            state = self._load_unlocked()
            strategy = state.setdefault("strategy_memory", deepcopy(EMPTY_STATE["strategy_memory"]))
            style_weight = strategy.setdefault("style_weight", {})
            source_weight = strategy.setdefault("source_weight", {})
            hashtag_weight = strategy.setdefault("hashtag_weight", {})
            metric_by_publish_id = {metric.get("publish_id"): metric for metric in performance_metrics or []}
            metric_by_mock_post_id = {metric.get("mock_post_id"): metric for metric in performance_metrics or []}
            for record in publish_records:
                style = record.get("style", "professional_news")
                metric = metric_by_publish_id.get(record.get("publish_id")) or metric_by_mock_post_id.get(record.get("mock_post_id"))
                score = metric.get("engagement_rate", 0) if metric else 0
                style_weight[style] = round(style_weight.get(style, 1.0) + min(score, 0.05), 3)
                for tag in record.get("hashtags", []):
                    hashtag_weight[tag] = round(hashtag_weight.get(tag, 1.0) + min(score / 2, 0.025), 3)
                cluster_id = record.get("cluster_id")
                if cluster_id:
                    source_weight[cluster_id] = round(source_weight.get(cluster_id, 1.0) + min(score / 3, 0.02), 3)
            self._write(state)

    def _write(self, state: Dict[str, Any]) -> None:
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        with self.state_file.open("w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)

    def _load_unlocked(self) -> Dict[str, Any]:
        with self.state_file.open("r", encoding="utf-8") as f:
            return json.load(f)

    @contextmanager
    def _locked(self):
        with self._thread_lock:
            if self._file_lock is None:
                yield
            else:
                with self._file_lock:
                    yield
