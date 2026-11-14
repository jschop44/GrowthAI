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


def test_shared_franchise_homepage_is_one_web_feature_observation():
    from backend.comparison import unique_site_peers, website_evidence_key
    target = observed_features('<h1>Roofing business</h1>', 'roofing')
    features = observed_features('<main><a href="/finance">Financing available</a></main>', 'roofing')
    rows = [
        {'name':'Chain branch A','website':'https://www.roofco.example/','features':features},
        {'name':'Chain branch B','website':'https://roofco.example','features':features},
        {'name':'Independent','website':'https://independent.example/','features':features},
        {'name':'Chain location page','website':'https://roofco.example/locations/branch-c','features':features},
    ]
    assert website_evidence_key(rows[0]['website']) == website_evidence_key(rows[1]['website'])
    unique = unique_site_peers(rows)
    assert len(unique) == 3
    assert [row['name'] for row in unique] == ['Chain branch A','Independent','Chain location page']
    comparison = compare_features(target, unique)
    financing = next(x for x in comparison if x['feature'] == 'financing')
    assert financing['competitors_scanned'] == 3
    assert financing['competitors_with_feature'] == ['Chain branch A','Independent','Chain location page']
    assert website_evidence_key('https://user:password@roofco.example/') is None
