from backend.comparison import observed_features, compare_features

def test_observed_feature_detection():
    page = '<html><body><a href="/order">Order Online</a></body></html>'
    found = observed_features(page, "pizza")
    assert found["online ordering"]["observed"] is True
    assert found["catering"]["observed"] is False

def test_competitor_feature_comparison():
    target = observed_features("<html><body>Welcome</body></html>", "roofing")
    rival = {"name": "Example rival", "features": observed_features("<html><body>Financing available</body></html>", "roofing")}
    rows = compare_features(target, [rival])
    financing = next(row for row in rows if row["feature"] == "financing")
    assert financing["target_observed"] is False
    assert financing["competitors_with_feature"] == ["Example rival"]
