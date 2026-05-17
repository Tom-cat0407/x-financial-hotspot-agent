from backend.app.clients.finance_data_client import CompositeFinanceDataClient
from backend.app.clients.alert_client import AlertClient
from backend.app.clients.telegram_client import TelegramClient
from backend.app.clients.threads_client import ThreadsClient


class FakeFinanceClient:
    def __init__(self, source):
        self.source = source

    def lookup_entities(self, entities):
        return {entity: {"source": self.source, "value": entity} for entity in entities}


def test_composite_finance_client_keeps_multiple_evidence_sources():
    client = CompositeFinanceDataClient(FakeFinanceClient("external"), FakeFinanceClient("mock"))
    result = client.lookup_entities(["Bitcoin"])
    assert isinstance(result["Bitcoin"], list)
    assert {item["source"] for item in result["Bitcoin"]} == {"external", "mock"}


def test_telegram_disabled_returns_skipped_record():
    result = TelegramClient(enabled=False).publish("hello")
    assert result["platform"] == "telegram"
    assert result["skipped"] is True


def test_threads_mock_publish_returns_mock_url():
    result = ThreadsClient(enabled=True).publish("hello")
    assert result["ok"] is True
    assert result["threads_post_url"].startswith("mock://threads/")


def test_alert_webhook_disabled_returns_skipped_record():
    result = AlertClient(webhook_url="").send("publish_failed", "hello", {"content_id": "cnt"})
    assert result["ok"] is False
    assert result["skipped"] is True
    assert result["reason"] == "alert_webhook_disabled"
