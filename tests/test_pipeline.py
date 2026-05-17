import pytest

from backend.app.clients.mock_x_client import MockXClient
from backend.app.services.memory_service import MemoryService
from backend.app.workflows import hotspot_pipeline
from backend.app.workflows.hotspot_pipeline import HotspotPipeline


def test_pipeline_generates_bilingual_ab_content_and_mock_posts(tmp_path):
    memory = MemoryService(state_file=tmp_path / "state.json")
    state = HotspotPipeline(MockXClient(), memory).run()
    assert len(state["raw_posts"]) >= 20
    assert len(state["event_clusters"]) >= 5
    # Default MAX_POSTS_PER_HOUR is 6; three clusters generate twelve bilingual A/B contents,
    # but only six are published automatically in one run.
    assert len(state["publish_records"]) == 6
    assert len(state["generated_contents"]) == 12
    assert len(state["performance_metrics"]) == len(state["publish_records"])
    assert len(state["ab_test_variants"]) == 12
    assert len(state["platform_dispatches"]) == len(state["publish_records"]) * 2
    assert any(variant["is_winner"] for variant in state["ab_test_variants"])
    assert any(variant["language"] == "zh" for variant in state["ab_test_variants"])
    assert all(card["alternate_cards"][0]["aspect_ratio"] == "1x1" for card in state["image_cards"])
    assert all(metric["engagement_rate"] > 0 for metric in state["performance_metrics"])
    assert any(content["language"] == "zh" for content in state["generated_contents"])
    assert any(
        "\u4e0d\u6784\u6210\u6295\u8d44\u5efa\u8bae" in content["tweet_text"]
        for content in state["generated_contents"]
        if content["language"] == "zh"
    )
    assert all(len(content["tweet_text"]) <= 280 for content in state["generated_contents"])


def test_pipeline_respects_max_posts_per_hour(monkeypatch, tmp_path):
    monkeypatch.setattr(hotspot_pipeline.settings, "max_posts_per_hour", 1)
    memory = MemoryService(state_file=tmp_path / "state.json")
    state = HotspotPipeline(MockXClient(), memory).run(publish_count=3)

    assert len(state["publish_records"]) == 1
    assert any(item["review_status"] == "rate_limited_waiting" for item in state["review_queue"])
    created = next(event for event in state["run_events"] if event["state"] == "created")
    assert created["payload"]["requested_publish_count"] == 3
    assert created["payload"]["effective_publish_count"] == 3
    assert created["payload"]["max_posts_per_hour"] == 1
    assert any(event["state"] == "publish_rate_limited" for event in state["run_events"])


def test_manual_approve_respects_max_posts_per_hour(monkeypatch, tmp_path):
    monkeypatch.setattr(hotspot_pipeline.settings, "max_posts_per_hour", 1)
    memory = MemoryService(state_file=tmp_path / "state.json")
    pipeline = HotspotPipeline(MockXClient(), memory)
    state = memory.load()
    state["publish_records"] = [{"ok": True, "publish_id": "pub_existing"}]
    state["generated_contents"] = [
        {
            "content_id": "cnt_manual",
            "cluster_id": "evt_manual",
            "tweet_text": "Market brief: manual approval. Not investment advice.",
            "style": "professional_news",
            "hashtags": ["#Markets"],
        }
    ]
    state["compliance_reports"] = [{"content_id": "cnt_manual", "compliance_report_id": "cmp_manual", "pass": True}]
    state["image_cards"] = [{"content_id": "cnt_manual", "card_path": "outputs/cards/missing.png"}]
    state["review_queue"] = [{"content_id": "cnt_manual", "review_status": "waiting"}]
    memory.replace_state(state)

    with pytest.raises(ValueError, match="Hourly publish cap"):
        pipeline.approve_and_publish("cnt_manual")

    next_state = memory.load()
    assert next_state["review_queue"][0]["review_status"] == "rate_limited_waiting"
    assert any(event["state"] == "publish_rate_limited" for event in next_state["run_events"])
