from backend.financial_intelligence import estimate_opportunities

def test_no_evidence_no_money():
    result = estimate_opportunities("roofing", [], [])
    assert result["opportunities"] == []

def test_scenarios_explicitly_hypothetical():
    competitor = {
        "name": "Example competitor", "status": "audited", "peer_eligible": True,
        "website": "https://roofer.example/",
        "features": {"Online quote": {"observed": True, "evidence_url": "https://roofer.example/",
                                       "scope": "analyzed homepage only"}},
    }
    result = estimate_opportunities("roofing", [competitor], [
        {"feature": "Online quote", "competitors_with_feature": ["Example competitor"]}
    ])
    item = result["opportunities"][0]
    assert item["confidence"] == "very low"
    assert "not observed lost revenue" in item["classification"]
    assert item["evidence_sources"] == [{"competitor": "Example competitor",
                                        "url": "https://roofer.example/",
                                        "scope": "analyzed homepage only"}]
    assert item["observed_competitors"] == 1
    values = item["annual_revenue_scenarios"]
    assert values["conservative"] < values["baseline"] < values["optimistic"]

def test_unknown_industry_no_fabricated_estimate():
    assert estimate_opportunities("unknown", [], [])["status"] == "unavailable"


def test_named_competitor_is_not_evidence_for_a_monetary_scenario():
    gaps = [{"feature": "financing", "competitors_with_feature": ["Claims Finance Inc"]}]
    assert estimate_opportunities("roofing", [], gaps)["status"] == "insufficient_evidence"
    for changed in (
        {"status": "not audited"},
        {"peer_eligible": False},
        {"features": {"financing": {"observed": False, "evidence_url": "https://finance.example/"}}},
        {"features": {"financing": {"observed": True, "evidence_url": "https://unrelated.example/"}}},
        {"website": "https://user:secret@finance.example/",
         "features": {"financing": {"observed": True, "evidence_url": "https://user:secret@finance.example/"}}},
    ):
        base = {"name": "Claims Finance Inc", "status": "audited", "peer_eligible": True,
                "website": "https://finance.example/",
                "features": {"financing": {"observed": True, "evidence_url": "https://finance.example/"}}}
        base.update(changed)
        report = estimate_opportunities("roofing", [base], gaps)
        assert report["opportunities"] == []
        assert report["status"] == "insufficient_evidence"


def test_evidence_linked_scenarios_count_independent_websites_not_duplicate_branches():
    evidence = {"observed": True, "evidence_url": "https://finance.example/",
                "scope": "analyzed homepage only"}
    peers = [
        {"name": "One Branch", "status": "audited", "peer_eligible": True,
         "website": "https://finance.example/", "features": {"financing": evidence}},
        {"name": "Other Branch", "status": "audited", "peer_eligible": True,
         "website": "https://finance.example/", "features": {"financing": evidence}},
        {"name": "Independent", "status": "audited", "peer_eligible": True,
         "website": "https://another.example/",
         "features": {"financing": {"observed": True, "evidence_url": "https://another.example/"}}},
    ]
    comparison = [{"feature": "financing",
                   "competitors_with_feature": ["One Branch", "Other Branch", "Independent"]}]
    result = estimate_opportunities("roofing", peers, comparison)
    assert result["status"] == "illustrative"
    item = result["opportunities"][0]
    assert item["observed_competitors"] == 2
    assert {x["url"] for x in item["evidence_sources"]} == {
        "https://finance.example/", "https://another.example/"}
    assert item["classification"] == "hypothetical scenario, not observed lost revenue"
    assert "not local market benchmarks" in result["limitations"][1]


def test_website_already_has_feature_cannot_generate_a_fictitious_missing_service_scenario():
    rival = {
        "name":"Local rival", "status":"audited", "peer_eligible":True,
        "website":"https://rival.example/",
        "features":{"financing":{"observed":True,"evidence_url":"https://rival.example/"}},
    }
    rows = [
        {"feature":"financing","target_observed":True,
         "competitors_with_feature":["Local rival"]},
        {"feature":"financing","target_observed":None,
         "target_status":"unknown","competitors_with_feature":["Local rival"]},
        {"feature":"financing","target_observed":"false",
         "competitors_with_feature":["Local rival"]},
    ]
    assert estimate_opportunities("roofing",[rival],rows)["status"]=="insufficient_evidence"
    assert estimate_opportunities("roofing",[rival],rows)["opportunities"]==[]
    actual_gap={"feature":"financing","target_observed":False,
                "competitors_with_feature":["Local rival"]}
    scenario=estimate_opportunities("roofing",[rival],[actual_gap])
    assert scenario["status"]=="illustrative"
    assert scenario["opportunities"][0]["feature"]=="financing"


def test_corrupt_opportunity_rows_cannot_crash_the_audit():
    assert estimate_opportunities("roofing",[],[None,False,"finance"])["status"]=="insufficient_evidence"
