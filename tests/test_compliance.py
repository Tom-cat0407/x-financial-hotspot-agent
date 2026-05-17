from backend.app.agents.compliance_guard_agent import compliance_check


def test_compliance_blocks_investment_advice():
    content = {
        "content_id": "cnt_1",
        "tweet_text": "Buy now, guaranteed return. Not investment advice.",
    }
    fact_check = {"verification_status": "verified"}
    report = compliance_check(content, fact_check)
    assert report["pass"] is False
    assert report["risk_level"] == "blocked"


def test_compliance_allows_neutral_disclaimer_content():
    content = {
        "content_id": "cnt_2",
        "tweet_text": "Market brief: Bitcoin ETF flows are being discussed by market sources. Not investment advice. #Bitcoin #ETF",
    }
    fact_check = {"verification_status": "mostly_verified"}
    report = compliance_check(content, fact_check)
    assert report["pass"] is True
    assert report["risk_level"] == "low"
