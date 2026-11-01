from backend.financial_intelligence import estimate_opportunities

def test_no_evidence_no_money():
    result = estimate_opportunities("roofing", [], [])
    assert result["opportunities"] == []

def test_scenarios_explicitly_hypothetical():
    result = estimate_opportunities("roofing", [], [
        {"feature": "Online quote", "competitors_with_feature": ["Example competitor"]}
    ])
    item = result["opportunities"][0]
    assert item["confidence"] == "very low"
    assert "not observed lost revenue" in item["classification"]
    values = item["annual_revenue_scenarios"]
    assert values["conservative"] < values["baseline"] < values["optimistic"]

def test_unknown_industry_no_fabricated_estimate():
    assert estimate_opportunities("unknown", [], [])["status"] == "unavailable"
