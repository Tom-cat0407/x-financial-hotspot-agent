from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

from backend.app.agents.collector_agent import collect_posts
from backend.app.agents.clusterer_agent import cluster_posts
from backend.app.agents.compliance_guard_agent import compliance_check
from backend.app.agents.emergency_priority_agent import classify_emergency
from backend.app.agents.entity_extractor_agent import extract_entities
from backend.app.agents.hashtag_agent import generate_hashtags
from backend.app.agents.image_card_agent import generate_image_card
from backend.app.agents.normalizer_agent import normalize_posts
from backend.app.agents.rag_fact_check_agent import fact_check_cluster
from backend.app.agents.tweet_generator_agent import generate_tweet
from backend.app.agents.agent_utils import write_report
from backend.app.clients.alert_client import AlertClient
from backend.app.clients.telegram_client import TelegramClient
from backend.app.clients.threads_client import ThreadsClient
from backend.app.clients.llm_client import LLMClient
from backend.app.clients.mock_x_client import MockXClient, MockXRateLimitError
from backend.app.core.config import settings
from backend.app.core.config_loader import load_accounts, load_keywords
from backend.app.clients.finance_data_client import CompositeFinanceDataClient, ExternalFinanceDataClient, MockFinanceDataClient
from backend.app.services.memory_service import MemoryService
from backend.app.services.scoring_service import calculate_hot_score


FALLBACK_ACCOUNTS = [
    "Bloomberg",
    "Reuters",
    "WSJ",
    "CoinDesk",
    "FinancialTimes",
    "MacroSignals",
    "CryptoDesk",
    "EquityBrief",
]

FALLBACK_KEYWORDS = ["Fed", "CPI", "ETF", "Bitcoin", "Ethereum", "SEC", "earnings", "rate cut", "Nvidia"]


class HotspotPipeline:
    def __init__(self, x_client: MockXClient, memory: MemoryService) -> None:
        self.x_client = x_client
        self.memory = memory
        self.llm_client = LLMClient.from_settings()
        self.finance_data_client = (
            CompositeFinanceDataClient(ExternalFinanceDataClient(), MockFinanceDataClient())
            if settings.enable_external_fact_sources
            else MockFinanceDataClient()
        )
        self.telegram_client = TelegramClient.from_settings()
        self.threads_client = ThreadsClient.from_settings()
        self.alert_client = AlertClient.from_settings()

    def run(self, top_n: int = 10, publish_count: int = 3, auto_approve: bool = True, reset_state: bool = True) -> Dict[str, Any]:
        requested_publish_count = publish_count
        publish_count = max(0, publish_count)
        publish_slots_remaining = settings.max_posts_per_hour
        existing_state = self.memory.load()
        previously_published = {record.get("cluster_id") for record in existing_state.get("publish_records", [])}
        if reset_state:
            self.memory.reset()
        self.x_client.reset_publications()
        self.memory.log_event(
            "created",
            "Pipeline run created.",
            {
                "reset_state": reset_state,
                "requested_publish_count": requested_publish_count,
                "effective_publish_count": publish_count,
                "max_posts_per_hour": settings.max_posts_per_hour,
            },
        )

        try:
            collection = collect_posts(self.x_client, load_accounts() or FALLBACK_ACCOUNTS, load_keywords() or FALLBACK_KEYWORDS)
            account_posts = collection["account_posts"]
            keyword_posts = collection["keyword_posts"]
            trending_topics = collection["trending_topics"]
        except MockXRateLimitError as exc:
            self.memory.log_event("failed", str(exc), {"endpoint": exc.endpoint, "reset_time": exc.reset_time})
            raise

        raw_posts = _dedupe_posts(account_posts + keyword_posts)
        self.memory.save("raw_posts", raw_posts)
        self.memory.log_event("collecting", f"Collected {len(raw_posts)} mock X posts.")

        normalized = normalize_posts(raw_posts)
        enriched = [
            extract_entities(post, llm_client=self.llm_client if _use_llm_ner(index) else None)
            for index, post in enumerate(normalized)
        ]
        self.memory.log_event("normalizing", "Posts normalized and entities extracted.")

        clusters = cluster_posts(enriched)
        for cluster in clusters:
            cluster["emergency"] = classify_emergency(cluster)
        self.memory.save("event_clusters", clusters)
        self.memory.log_event("clustering", f"Built {len(clusters)} event clusters.")

        scores = [calculate_hot_score(cluster, trending_topics) for cluster in clusters]
        score_by_cluster = {score["cluster_id"]: score for score in scores}
        ranked_clusters = sorted(clusters, key=lambda c: score_by_cluster[c["cluster_id"]]["hot_score"], reverse=True)[:top_n]
        self.memory.save("hot_scores", scores)
        self.memory.log_event("scoring", f"Ranked Top {len(ranked_clusters)} hotspots.")

        fact_checks = []
        generated_contents = []
        compliance_reports = []
        image_cards = []
        review_queue = []
        publish_records = []
        platform_dispatches = []
        performance_metrics = []
        ab_test_variants = []

        publish_candidates = [cluster for cluster in ranked_clusters if reset_state or cluster["cluster_id"] not in previously_published]
        for cluster in publish_candidates[:publish_count]:
            self.memory.log_event("generating", f"Generating content for {cluster['cluster_id']}.")
            fact_check = fact_check_cluster(cluster, finance_client=self.finance_data_client)
            fact_checks.append(fact_check)
            style = _style_for_cluster(cluster)
            hashtags = generate_hashtags(cluster, trending_topics, language="en")
            zh_hashtags = generate_hashtags(cluster, trending_topics, language="zh")
            self.memory.log_event("llm_content", f"Requesting English A copy for {cluster['cluster_id']}.")
            content = generate_tweet(cluster, fact_check, hashtags, style=style, language="en", llm_client=self.llm_client)
            content["experiment_id"] = f"ab_{cluster['cluster_id']}"
            content["variant_id"] = f"ab_{cluster['cluster_id']}_a"
            content["variant_name"] = "A"
            content["language_variant"] = "en"
            self.memory.log_event("llm_content", f"Requesting Chinese companion copy for {cluster['cluster_id']}.")
            zh_content = generate_tweet(cluster, fact_check, zh_hashtags, style=style, language="zh", llm_client=self.llm_client)
            zh_content.update(
                {
                    "experiment_id": f"ab_{cluster['cluster_id']}_zh",
                    "variant_id": f"ab_{cluster['cluster_id']}_zh_a",
                    "variant_name": "A",
                    "language_variant": "zh",
                }
            )
            content["localized_variants"] = {"zh": zh_content}
            variant_contents = [content, zh_content]
            if settings.enable_ab_testing:
                alt_style = _alternate_style(style)
                self.memory.log_event("llm_content", f"Requesting English B copy for {cluster['cluster_id']}.")
                alt_content = generate_tweet(cluster, fact_check, hashtags, style=alt_style, language="en", llm_client=self.llm_client)
                alt_content.update(
                    {
                        "content_id": f"cnt_{cluster['cluster_id']}_en_b",
                        "experiment_id": f"ab_{cluster['cluster_id']}",
                        "variant_id": f"ab_{cluster['cluster_id']}_b",
                        "variant_name": "B",
                        "language_variant": "en",
                    }
                )
                variant_contents.append(alt_content)
                self.memory.log_event("llm_content", f"Requesting Chinese B copy for {cluster['cluster_id']}.")
                zh_alt_content = generate_tweet(cluster, fact_check, zh_hashtags, style=alt_style, language="zh", llm_client=self.llm_client)
                zh_alt_content.update(
                    {
                        "content_id": f"cnt_{cluster['cluster_id']}_zh_b",
                        "experiment_id": f"ab_{cluster['cluster_id']}_zh",
                        "variant_id": f"ab_{cluster['cluster_id']}_zh_b",
                        "variant_name": "B",
                        "language_variant": "zh",
                    }
                )
                variant_contents.append(zh_alt_content)
            for variant_content in variant_contents:
                generated_contents.append(variant_content)
                self.memory.log_event("llm_compliance", f"Reviewing variant {variant_content.get('variant_name')} for {cluster['cluster_id']}.")
                compliance = compliance_check(variant_content, fact_check, llm_client=self.llm_client)
                compliance["report_path"] = write_report(compliance)
                compliance_reports.append(compliance)
                card = generate_image_card(cluster, score_by_cluster[cluster["cluster_id"]], variant_content)
                card["variant_id"] = variant_content.get("variant_id")
                image_cards.append(card)
                ab_test_variants.append(
                    {
                        "variant_id": variant_content.get("variant_id"),
                        "experiment_id": variant_content.get("experiment_id"),
                        "variant_name": variant_content.get("variant_name"),
                        "language": variant_content.get("language"),
                        "cluster_id": cluster["cluster_id"],
                        "content_id": variant_content["content_id"],
                        "style": variant_content["style"],
                        "card_path": card["card_path"],
                        "status": "approved" if auto_approve and compliance["pass"] else "waiting",
                        "is_winner": False,
                    }
                )
                review_item = {
                    "review_id": f"rev_{variant_content['content_id']}",
                    "content_id": variant_content["content_id"],
                    "cluster_id": cluster["cluster_id"],
                    "tweet_text": variant_content["tweet_text"],
                    "zh_tweet_text": zh_content["tweet_text"] if variant_content is content else "",
                    "language": variant_content.get("language"),
                    "risk_level": compliance["risk_level"],
                    "review_status": "approved" if auto_approve and compliance["pass"] else "waiting",
                    "variant_id": variant_content.get("variant_id"),
                    "variant_name": variant_content.get("variant_name"),
                }
                review_queue.append(review_item)
                if review_item["review_status"] == "approved":
                    if publish_slots_remaining > 0:
                        publish_records.append(self._publish(variant_content, compliance, card))
                        publish_slots_remaining -= 1
                    else:
                        review_item["review_status"] = "rate_limited_waiting"
                        self.memory.log_event(
                            "publish_rate_limited",
                            f"Hourly publish cap reached; queued {variant_content['content_id']}.",
                            {
                                "content_id": variant_content["content_id"],
                                "max_posts_per_hour": settings.max_posts_per_hour,
                                "alert": self._send_alert(
                                    "publish_rate_limited",
                                    "Hourly publish cap reached.",
                                    {"content_id": variant_content["content_id"], "max_posts_per_hour": settings.max_posts_per_hour},
                                ),
                            },
                        )
        if publish_records:
            performance_metrics = self.refresh_performance_metrics(publish_records, persist=False)
            ab_test_variants = _evaluate_ab_tests(ab_test_variants, publish_records, performance_metrics)
            platform_dispatches = [dispatch for record in publish_records for dispatch in record.get("platform_dispatches", [])]

        self.memory.save("fact_checks", fact_checks)
        self.memory.save("generated_contents", generated_contents)
        self.memory.save("compliance_reports", compliance_reports)
        self.memory.save("image_cards", image_cards)
        self.memory.save("review_queue", review_queue)
        self.memory.save("publish_records", publish_records)
        self.memory.save("platform_dispatches", platform_dispatches)
        self.memory.save("performance_metrics", performance_metrics)
        self.memory.save("ab_test_variants", ab_test_variants)
        self.memory.update_strategy_after_publish(publish_records, performance_metrics)
        self.memory.log_event("completed", f"Generated {len(generated_contents)} contents and published {len(publish_records)} mock posts.")

        state = self.memory.load()
        state["llm_enabled"] = self.llm_client.enabled
        state["top_hotspots"] = [
            {
                **cluster,
                "hot_score": score_by_cluster[cluster["cluster_id"]]["hot_score"],
                "score_breakdown": score_by_cluster[cluster["cluster_id"]]["score_breakdown"],
            }
            for cluster in ranked_clusters
        ]
        state["trending_topics"] = trending_topics
        self.memory.replace_state(state)
        return state

    def approve_and_publish(self, content_id: str) -> Dict[str, Any]:
        state = self.memory.load()
        if _published_count(state.get("publish_records", [])) >= settings.max_posts_per_hour:
            for item in state.get("review_queue", []):
                if item.get("content_id") == content_id:
                    item["review_status"] = "rate_limited_waiting"
            self.memory.replace_state(state)
            self.memory.log_event(
                "publish_rate_limited",
                f"Hourly publish cap reached; manual approval queued {content_id}.",
                {
                    "content_id": content_id,
                    "max_posts_per_hour": settings.max_posts_per_hour,
                    "alert": self._send_alert(
                        "publish_rate_limited",
                        "Hourly publish cap reached during manual approval.",
                        {"content_id": content_id, "max_posts_per_hour": settings.max_posts_per_hour},
                    ),
                },
            )
            raise ValueError("Hourly publish cap reached; content remains queued.")
        content = next(c for c in state["generated_contents"] if c["content_id"] == content_id)
        compliance = next(c for c in state["compliance_reports"] if c["content_id"] == content_id)
        card = next(c for c in state["image_cards"] if c["content_id"] == content_id)
        if not compliance["pass"]:
            raise ValueError("Content did not pass compliance review.")
        record = self._publish(content, compliance, card)
        state["publish_records"].append(record)
        metric = self._performance_metric(record) if record.get("ok") else None
        if metric:
            state.setdefault("performance_metrics", []).append(metric)
        state.setdefault("platform_dispatches", []).extend(record.get("platform_dispatches", []))
        for item in state["review_queue"]:
            if item["content_id"] == content_id:
                item["review_status"] = "approved"
        self.memory.replace_state(state)
        self.memory.update_strategy_after_publish([record], [metric] if metric else [])
        return record

    def refresh_performance_metrics(
        self,
        publish_records: List[Dict[str, Any]] | None = None,
        persist: bool = True,
    ) -> List[Dict[str, Any]]:
        state = self.memory.load() if persist or publish_records is None else None
        if publish_records is None:
            publish_records = (state or {}).get("publish_records", [])
        metrics = [self._performance_metric(record) for record in publish_records if record.get("ok")]
        if persist:
            next_state = state or {}
            next_state["performance_metrics"] = metrics
            self.memory.replace_state(next_state)
            self.memory.update_strategy_after_publish(publish_records, metrics)
            self.memory.log_event("feedback", f"Refreshed {len(metrics)} performance metrics.")
        return metrics

    def _publish(self, content: Dict[str, Any], compliance: Dict[str, Any], card: Dict[str, Any]) -> Dict[str, Any]:
        upload = self.x_client.upload_media(card["card_path"])
        response = self._create_post_with_retry(content["tweet_text"], upload["media_id"], content)
        record = {
            **response,
            "mode": "mock",
            "cluster_id": content["cluster_id"],
            "content_id": content["content_id"],
            "style": content["style"],
            "review_status": "approved",
            "compliance_report_id": compliance["compliance_report_id"],
            "card_path": card["card_path"],
            "hashtags": content.get("hashtags", []),
            "experiment_id": content.get("experiment_id"),
            "variant_id": content.get("variant_id"),
            "variant_name": content.get("variant_name"),
        }
        if record.get("ok"):
            record["platform_dispatches"] = self._dispatch_multiplatform(content, record)
        else:
            record.setdefault("publish_id", f"pub_failed_{content['content_id']}")
            record["platform_dispatches"] = []
            self.memory.log_event(
                "publish_failed",
                f"Publish failed for {content['content_id']}: {record.get('error', 'unknown')}.",
                {
                    "content_id": content["content_id"],
                    "status_code": record.get("status_code"),
                    "error": record.get("error"),
                    "alert": self._send_alert(
                        "publish_failed",
                        "Publish failed after retry attempts.",
                        {"content_id": content["content_id"], "status_code": record.get("status_code"), "error": record.get("error")},
                    ),
                },
            )
        return record

    def _create_post_with_retry(self, text: str, media_id: str, content: Dict[str, Any]) -> Dict[str, Any]:
        attempts = []
        max_attempts = settings.publish_max_retries + 1
        for attempt in range(1, max_attempts + 1):
            try:
                response = self.x_client.create_post(text, media_id=media_id)
            except MockXRateLimitError as exc:
                attempts.append({"attempt": attempt, "ok": False, "status_code": 429, "error": str(exc), "reset_time": exc.reset_time})
                self.memory.log_event(
                    "publish_retry",
                    f"Publish rate limited for {content['content_id']} on attempt {attempt}.",
                    {
                        "content_id": content["content_id"],
                        "attempt": attempt,
                        "endpoint": exc.endpoint,
                        "reset_time": exc.reset_time,
                        "alert": self._send_alert(
                            "publish_retry",
                            "Publish rate limited; retrying.",
                            {"content_id": content["content_id"], "attempt": attempt, "endpoint": exc.endpoint},
                        ),
                    },
                )
                if attempt >= max_attempts:
                    return {
                        "ok": False,
                        "status_code": 429,
                        "error": str(exc),
                        "reset_time": exc.reset_time,
                        "publish_attempts": attempts,
                        "publish_retry_count": attempt - 1,
                    }
                continue
            attempts.append(
                {
                    "attempt": attempt,
                    "ok": response.get("ok", False),
                    "status_code": response.get("status_code"),
                    "error": response.get("error"),
                }
            )
            if response.get("ok"):
                response["publish_attempts"] = attempts
                response["publish_retry_count"] = attempt - 1
                return response
            self.memory.log_event(
                "publish_retry",
                f"Publish failed for {content['content_id']} on attempt {attempt}: {response.get('error', 'unknown')}.",
                {
                    "content_id": content["content_id"],
                    "attempt": attempt,
                    "status_code": response.get("status_code"),
                    "error": response.get("error"),
                    "alert": self._send_alert(
                        "publish_retry",
                        "Publish failed; retrying if allowed.",
                        {
                            "content_id": content["content_id"],
                            "attempt": attempt,
                            "status_code": response.get("status_code"),
                            "error": response.get("error"),
                        },
                    ),
                },
            )
            if not _is_retryable_publish_failure(response) or attempt >= max_attempts:
                response["publish_attempts"] = attempts
                response["publish_retry_count"] = attempt - 1
                return response
        return {"ok": False, "status_code": 500, "error": "publish_retry_exhausted", "publish_attempts": attempts, "publish_retry_count": settings.publish_max_retries}

    def _send_alert(self, event_type: str, message: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self.alert_client.send(event_type, message, payload)

    def _dispatch_multiplatform(self, content: Dict[str, Any], publish_record: Dict[str, Any]) -> List[Dict[str, Any]]:
        dispatches = []
        for platform, result in [
            ("telegram", self.telegram_client.publish(content["tweet_text"], publish_record.get("mock_post_url", ""))),
            ("threads", self.threads_client.publish(content["tweet_text"], publish_record.get("mock_post_url", ""))),
        ]:
            dispatches.append(
                {
                    "dispatch_id": f"dist_{publish_record['publish_id']}_{platform}",
                    "publish_id": publish_record["publish_id"],
                    "content_id": content["content_id"],
                    "cluster_id": content["cluster_id"],
                    "platform": platform,
                    **result,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
            )
        return dispatches

    def _performance_metric(self, record: Dict[str, Any]) -> Dict[str, Any]:
        metrics = self.x_client.fetch_post_metrics(record["mock_post_id"])
        engagements = (
            metrics.get("like_count", 0)
            + metrics.get("repost_count", 0)
            + metrics.get("reply_count", 0)
            + metrics.get("quote_count", 0)
        )
        views = max(metrics.get("view_count", 0), 1)
        return {
            "performance_metric_id": f"perf_{record['publish_id']}",
            "publish_id": record["publish_id"],
            "mock_post_id": record["mock_post_id"],
            "cluster_id": record["cluster_id"],
            "content_id": record["content_id"],
            "experiment_id": record.get("experiment_id"),
            "variant_id": record.get("variant_id"),
            "variant_name": record.get("variant_name"),
            "like_count": metrics.get("like_count", 0),
            "repost_count": metrics.get("repost_count", 0),
            "reply_count": metrics.get("reply_count", 0),
            "quote_count": metrics.get("quote_count", 0),
            "view_count": metrics.get("view_count", 0),
            "engagement_count": engagements,
            "engagement_rate": round(engagements / views, 4),
            "collected_at": datetime.now(timezone.utc).isoformat(),
            "source": "mock_x_metrics",
        }


def _dedupe_posts(posts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    result = []
    for post in posts:
        if post["post_id"] not in seen:
            seen.add(post["post_id"])
            result.append(post)
    return result


def _style_for_cluster(cluster: Dict[str, Any]) -> str:
    if cluster.get("emergency", {}).get("emergency_level") in {"high", "medium"}:
        return "professional_news"
    if cluster["event_type"] == "central_bank":
        return "educational"
    return "commentary"


def _alternate_style(style: str) -> str:
    alternatives = {
        "professional_news": "educational",
        "educational": "commentary",
        "commentary": "professional_news",
    }
    return alternatives.get(style, "commentary")


def _use_llm_ner(index: int) -> bool:
    if not settings.enable_llm_ner:
        return False
    return index < settings.llm_ner_max_posts_per_run


def _is_retryable_publish_failure(response: Dict[str, Any]) -> bool:
    status_code = int(response.get("status_code") or 0)
    return status_code in {408, 409, 425, 429} or status_code >= 500


def _published_count(publish_records: List[Dict[str, Any]]) -> int:
    return sum(1 for record in publish_records if record.get("ok"))


def _evaluate_ab_tests(
    variants: List[Dict[str, Any]],
    publish_records: List[Dict[str, Any]],
    performance_metrics: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    publish_by_variant = {record.get("variant_id"): record for record in publish_records if record.get("variant_id")}
    metric_by_variant = {metric.get("variant_id"): metric for metric in performance_metrics if metric.get("variant_id")}
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for variant in variants:
        variant_id = variant.get("variant_id")
        publish = publish_by_variant.get(variant_id, {})
        metric = metric_by_variant.get(variant_id, {})
        variant.update(
            {
                "publish_id": publish.get("publish_id"),
                "mock_post_id": publish.get("mock_post_id"),
                "performance_metric_id": metric.get("performance_metric_id"),
                "engagement_rate": metric.get("engagement_rate", 0),
                "status": "published" if publish.get("ok") else variant.get("status", "waiting"),
            }
        )
        grouped.setdefault(variant.get("experiment_id", ""), []).append(variant)
    for experiment_variants in grouped.values():
        if len(experiment_variants) < 2:
            continue
        winner = max(experiment_variants, key=lambda item: item.get("engagement_rate", 0))
        for variant in experiment_variants:
            variant["is_winner"] = variant is winner and variant.get("engagement_rate", 0) > 0
    return variants
