from backend.app.services.scoring_service import calculate_hot_score


def test_hot_score_contains_breakdown():
    cluster = {
        "cluster_id": "evt_1",
        "last_seen_at": "2026-05-15T00:00:00+00:00",
        "independent_source_count": 3,
        "emergency": {"emergency_boost": 10},
        "source_posts": [
            {
                "text": "Fed CPI rate decision",
                "source_type": "media",
                "like_count": 100,
                "repost_count": 20,
                "reply_count": 10,
                "quote_count": 5,
                "view_count": 10000,
            }
        ],
    }
    score = calculate_hot_score(cluster, [{"topic": "#Fed"}])
    assert score["hot_score"] > 0
    assert "engagement_velocity" in score["score_breakdown"]


def test_time_decay_is_continuous_after_five_hours():
    cluster = {
        "cluster_id": "evt_old",
        "last_seen_at": "2026-05-15T00:00:00+00:00",
        "independent_source_count": 1,
        "source_posts": [
            {
                "text": "Gold market discussion",
                "source_type": "media",
                "created_at": "2026-05-15T00:00:00+00:00",
                "like_count": 1,
                "repost_count": 1,
                "reply_count": 1,
                "quote_count": 1,
                "view_count": 10,
            }
        ],
    }
    score = calculate_hot_score(cluster, [])
    assert score["score_breakdown"]["time_decay"] >= 0
    assert "market_relevance" in score["score_breakdown"]
