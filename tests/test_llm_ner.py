from backend.app.agents.entity_extractor_agent import extract_entities


class FakeNERClient:
    enabled = True

    def extract_financial_entities(self, payload):
        return {
            "entities": ["Jerome Powell", "United States"],
            "event_type": "central_bank",
            "entity_types": {"Jerome Powell": "person", "United States": "country_region"},
        }


class DuplicateNERClient:
    enabled = True

    def extract_financial_entities(self, payload):
        return {
            "entities": ["Fed", "Fed", "Jerome Powell"],
            "event_type": "policy_change",
            "entity_types": {"Jerome Powell": "person"},
        }


class DisabledNERClient:
    enabled = False

    def extract_financial_entities(self, payload):
        raise AssertionError("disabled LLM client should not be called")


class NoneNERClient:
    enabled = True

    def extract_financial_entities(self, payload):
        return None


def test_llm_ner_augments_rule_entities(monkeypatch):
    monkeypatch.setattr("backend.app.agents.entity_extractor_agent.settings.enable_llm_ner", True)
    post = {
        "post_id": "ner_1",
        "author_handle": "Reuters",
        "lang": "en",
        "text": "Powell says the Fed is watching inflation in the United States.",
        "text_clean": "Powell says the Fed is watching inflation in the United States.",
    }
    enriched = extract_entities(post, llm_client=FakeNERClient())
    assert "Fed" in enriched["entities"]
    assert "Jerome Powell" in enriched["entities"]
    assert enriched["entity_types"]["Jerome Powell"] == "person"
    assert enriched["event_type"] == "central_bank"


def test_llm_ner_dedupes_entities_and_ignores_unknown_event_type(monkeypatch):
    monkeypatch.setattr("backend.app.agents.entity_extractor_agent.settings.enable_llm_ner", True)
    post = {
        "post_id": "ner_2",
        "author_handle": "Reuters",
        "lang": "en",
        "text": "Powell says the Fed is watching inflation.",
        "text_clean": "Powell says the Fed is watching inflation.",
    }

    enriched = extract_entities(post, llm_client=DuplicateNERClient())

    assert enriched["entities"].count("Fed") == 1
    assert "Jerome Powell" in enriched["entities"]
    assert enriched["event_type"] == "central_bank"


def test_llm_ner_skips_disabled_client(monkeypatch):
    monkeypatch.setattr("backend.app.agents.entity_extractor_agent.settings.enable_llm_ner", True)
    post = {
        "post_id": "ner_3",
        "author_handle": "Reuters",
        "lang": "en",
        "text": "The Fed is watching inflation.",
        "text_clean": "The Fed is watching inflation.",
    }

    enriched = extract_entities(post, llm_client=DisabledNERClient())

    assert "Fed" in enriched["entities"]
    assert "Jerome Powell" not in enriched["entities"]
    assert enriched["entity_types"] == {}


def test_llm_ner_handles_none_response(monkeypatch):
    monkeypatch.setattr("backend.app.agents.entity_extractor_agent.settings.enable_llm_ner", True)
    post = {
        "post_id": "ner_4",
        "author_handle": "Reuters",
        "lang": "en",
        "text": "The SEC comments on Bitcoin ETF flows.",
        "text_clean": "The SEC comments on Bitcoin ETF flows.",
    }

    enriched = extract_entities(post, llm_client=NoneNERClient())

    assert "SEC" in enriched["entities"]
    assert "Bitcoin" in enriched["entities"]
    assert enriched["entity_types"] == {}
