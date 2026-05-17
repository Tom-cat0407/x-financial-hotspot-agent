from PIL import Image

from backend.app.agents.card_utils import _render_pillow_card
from backend.app.agents.clusterer_agent import cluster_posts
from backend.app.agents.entity_extractor_agent import extract_entities
from backend.app.agents.normalizer_agent import normalize_posts
from backend.app.agents.tweet_generator_agent import generate_tweet


def test_clusterer_handles_empty_input():
    assert cluster_posts([]) == []


def test_clusterer_handles_single_post():
    posts = normalize_posts(
        [
            {
                "post_id": "single",
                "author_handle": "Reuters",
                "source_type": "media",
                "text": "Gold market discussion follows Treasury yield moves",
                "created_at": "2026-05-15T00:00:00+00:00",
                "like_count": 1,
                "repost_count": 1,
                "reply_count": 1,
                "quote_count": 1,
                "view_count": 10,
            }
        ]
    )
    clusters = cluster_posts([extract_entities(posts[0])])
    assert len(clusters) == 1
    assert clusters[0]["source_count"] == 1


class LongTextLLM:
    enabled = True

    def generate_tweet(self, payload):
        return "Market brief: " + ("Bitcoin ETF liquidity discussion " * 20) + " #Bitcoin #ETF"


def test_llm_tweet_is_truncated_and_keeps_disclaimer():
    cluster = {
        "cluster_id": "evt_test",
        "main_title": "Bitcoin ETF discussion",
        "summary": "Multiple sources discuss Bitcoin ETF liquidity.",
        "entities": ["Bitcoin", "ETF"],
        "event_type": "crypto_etf",
        "source_count": 3,
    }
    fact_check = {"verification_status": "mostly_verified", "risk_note": ""}
    content = generate_tweet(cluster, fact_check, ["#Bitcoin", "#ETF"], llm_client=LongTextLLM())
    assert len(content["tweet_text"]) <= 280
    assert "Not investment advice." in content["tweet_text"]


def test_llm_tweet_backfills_missing_hashtags():
    class NoHashtagLLM:
        enabled = True

        def generate_tweet(self, payload):
            return "ETF desks are discussing renewed Bitcoin inflow momentum. Not investment advice."

    cluster = {
        "cluster_id": "evt_hash",
        "main_title": "Bitcoin ETF inflow watch",
        "summary": "Bitcoin ETF inflows are being discussed by market desks.",
        "entities": ["Bitcoin", "ETF"],
        "event_type": "crypto_etf",
        "source_count": 2,
    }
    fact_check = {"verification_status": "mostly_verified", "risk_note": ""}

    content = generate_tweet(
        cluster,
        fact_check,
        ["#Bitcoin", "#ETF", "#Crypto", "#Markets"],
        llm_client=NoHashtagLLM(),
    )

    assert len(content["tweet_text"]) <= 280
    assert content["tweet_text"].count("#") >= 3


def test_pillow_square_card_fallback_uses_1x1_canvas(tmp_path):
    cluster = {
        "cluster_id": "evt_card",
        "main_title": "Bitcoin ETF liquidity watch across multiple desks",
        "event_type": "crypto_etf",
        "entities": ["Bitcoin", "ETF", "SEC"],
        "source_count": 3,
        "emergency": {"emergency_level": "low"},
    }
    score = {
        "hot_score": 82.4,
        "score_breakdown": {
            "EngagementVelocity": 24,
            "SourceAuthority": 18,
            "CrossSourceConfirmation": 12,
            "MarketRelevance": 15,
        },
    }
    content = {
        "tweet_text": "Market brief: ETF desks are discussing Bitcoin liquidity across several sources. Not investment advice. #Bitcoin #ETF #Markets",
    }
    output = tmp_path / "square.png"

    _render_pillow_card(cluster, score, content, output, aspect_ratio="1x1")

    with Image.open(output) as image:
        assert image.size == (1080, 1080)
