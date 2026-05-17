from backend.app.clients.mock_x_client import MockXClient
from backend.app.services.memory_service import MemoryService
from backend.app.workflows.hotspot_pipeline import HotspotPipeline


def test_mock_x_client_creates_post_url():
    client = MockXClient()
    response = client.create_post("Market brief: neutral content. Not investment advice.")
    assert response["ok"] is True
    assert response["mock_post_url"].endswith("/mock_x/posts/mock_post_001")


def test_mock_x_client_rejects_duplicate_content():
    client = MockXClient()
    text = "Market brief: duplicate content. Not investment advice."
    assert client.create_post(text)["ok"] is True
    assert client.create_post(text)["status_code"] == 409


def test_mock_x_client_returns_metrics_for_published_mock_post():
    client = MockXClient()
    response = client.create_post("Market brief: neutral content. Not investment advice.")
    metrics = client.fetch_post_metrics(response["mock_post_id"])
    assert metrics["post_id"] == response["mock_post_id"]
    assert metrics["view_count"] > 0
    assert metrics["like_count"] > 0


def test_pipeline_retries_retryable_publish_failure(tmp_path):
    class FlakyPublishClient(MockXClient):
        def __init__(self):
            super().__init__()
            self.create_calls = 0

        def create_post(self, text, media_id=None):
            self.create_calls += 1
            if self.create_calls == 1:
                return {"ok": False, "status_code": 500, "error": "temporary_publish_failure"}
            return super().create_post(text, media_id=media_id)

    client = FlakyPublishClient()
    memory = MemoryService(state_file=tmp_path / "state.json")
    pipeline = HotspotPipeline(client, memory)
    record = pipeline._create_post_with_retry(
        "Market brief: retryable post. Not investment advice.",
        "mock_media_retry",
        {"content_id": "cnt_retry"},
    )

    assert record["ok"] is True
    assert record["publish_retry_count"] == 1
    assert client.create_calls == 2
    state = memory.load()
    assert any(event["state"] == "publish_retry" for event in state["run_events"])


def test_pipeline_returns_failed_record_after_rate_limit_retries(tmp_path):
    client = MockXClient()
    client.simulate_429("create_post")
    memory = MemoryService(state_file=tmp_path / "state.json")
    pipeline = HotspotPipeline(client, memory)
    record = pipeline._create_post_with_retry(
        "Market brief: rate limited post. Not investment advice.",
        "mock_media_rate_limit",
        {"content_id": "cnt_rate_limit"},
    )

    assert record["ok"] is False
    assert record["status_code"] == 429
    assert record["publish_retry_count"] == 2
    assert len(record["publish_attempts"]) == 3
    state = memory.load()
    assert any(event["state"] == "publish_retry" for event in state["run_events"])
