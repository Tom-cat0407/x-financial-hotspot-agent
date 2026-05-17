import json
import http.client

from backend.app.clients.llm_client import LLMClient


class FakeResponse:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return json.dumps({"choices": [{"message": {"content": "ok"}}]}).encode("utf-8")


def test_thinking_payload_is_sent_as_top_level_field(monkeypatch):
    captured = {}

    def fake_urlopen(request, timeout):
        captured["body"] = json.loads(request.data.decode("utf-8"))
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    client = LLMClient(
        api_key="test-key",
        base_url="https://api.deepseek.com",
        model="deepseek-v4-pro",
        timeout_seconds=12,
        reasoning_effort="high",
        thinking_enabled=True,
    )

    assert client.generate_tweet({"cluster": {"title": "x"}}) == "ok"

    assert captured["body"]["reasoning_effort"] == "high"
    assert captured["body"]["thinking"] == {"type": "enabled"}
    assert "extra_body" not in captured["body"]
    assert captured["timeout"] == 12


def test_structured_json_calls_skip_reasoning(monkeypatch):
    captured = {}

    def fake_urlopen(request, timeout):
        captured["body"] = json.loads(request.data.decode("utf-8"))
        return FakeResponse()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    client = LLMClient(
        api_key="test-key",
        base_url="https://api.deepseek.com",
        model="deepseek-v4-pro",
        reasoning_effort="high",
        thinking_enabled=True,
    )

    client.review_compliance({"content": "Market update. Not investment advice."})

    assert "reasoning_effort" not in captured["body"]
    assert "thinking" not in captured["body"]
    assert captured["body"]["response_format"] == {"type": "json_object"}


def test_transient_transport_error_retries(monkeypatch):
    calls = {"count": 0}

    def fake_urlopen(request, timeout):
        calls["count"] += 1
        if calls["count"] == 1:
            raise http.client.IncompleteRead(b"")
        return FakeResponse()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    monkeypatch.setattr("time.sleep", lambda seconds: None)
    client = LLMClient(
        api_key="test-key",
        base_url="https://api.deepseek.com",
        model="deepseek-v4-pro",
        max_retries=2,
        retry_base_seconds=0,
    )

    assert client.generate_tweet({"cluster": {"title": "x"}}) == "ok"
    assert calls["count"] == 2
