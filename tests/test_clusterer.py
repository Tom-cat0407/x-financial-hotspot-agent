from backend.app.agents.clusterer_agent import cluster_posts
from backend.app.agents.entity_extractor_agent import extract_entities
from backend.app.agents.normalizer_agent import normalize_posts


def test_clusterer_merges_same_event_posts():
    posts = normalize_posts(
        [
            {
                "post_id": "a",
                "author_handle": "Bloomberg",
                "source_type": "media",
                "text": "Bitcoin ETF inflow discussion",
                "created_at": "2026-05-15T00:00:00+00:00",
                "like_count": 1,
                "repost_count": 1,
                "reply_count": 1,
                "quote_count": 1,
                "view_count": 10,
            },
            {
                "post_id": "b",
                "author_handle": "CoinDesk",
                "source_type": "media",
                "text": "BTC ETF inflows remain in focus",
                "created_at": "2026-05-15T00:01:00+00:00",
                "like_count": 1,
                "repost_count": 1,
                "reply_count": 1,
                "quote_count": 1,
                "view_count": 10,
            },
        ]
    )
    enriched = [extract_entities(post) for post in posts]
    clusters = cluster_posts(enriched)
    assert len(clusters) == 1
    assert clusters[0]["source_count"] == 2
    assert "ETF" in clusters[0]["entities"]


def test_clusterer_does_not_depend_on_predefined_cluster_key():
    posts = normalize_posts(
        [
            {
                "post_id": "a",
                "author_handle": "Bloomberg",
                "source_type": "media",
                "text": "Treasury yields rise as Fed inflation expectations shift",
                "created_at": "2026-05-15T00:00:00+00:00",
                "like_count": 1,
                "repost_count": 1,
                "reply_count": 1,
                "quote_count": 1,
                "view_count": 10,
            },
            {
                "post_id": "b",
                "author_handle": "BondDesk",
                "source_type": "kol",
                "text": "Fed inflation repricing pushes Treasury yields higher",
                "created_at": "2026-05-15T00:03:00+00:00",
                "like_count": 1,
                "repost_count": 1,
                "reply_count": 1,
                "quote_count": 1,
                "view_count": 10,
            },
        ]
    )
    enriched = [extract_entities(post) for post in posts]
    clusters = cluster_posts(enriched)
    assert len(clusters) == 1
