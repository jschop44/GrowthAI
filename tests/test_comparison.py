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


def test_hidden_product_and_booking_templates_are_not_observed_homepage_features():
    page = '''
    <html><body>
      <div hidden><a href="/order-online">Order Online</a></div>
      <section aria-hidden="true"><p>Catering available</p></section>
      <div style="display: none"><a href="/delivery">Delivery</a></div>
      <section style="visibility : hidden !important"><a href="/menu">Menu</a></section>
      <template><a href="/order-online">Order now</a></template>
      <svg><text>catering</text></svg>
      <div inert><a href="/delivery">Delivery</a></div>
      <p>Our neighborhood pizza kitchen is now open.</p>
    </body></html>
    '''
    findings = observed_features(page, "pizza", "https://pizza.example")
    for name in ("online ordering", "menu", "catering", "delivery"):
        assert findings[name]["observed"] is False, name
        assert findings[name]["evidence_url"] is None


def test_visible_features_still_count_and_hidden_rivals_cannot_create_false_gaps():
    target = observed_features('<h1>Neighborhood Pizza</h1>', "pizza")
    hidden_rival = {
        "name": "Unverified Rival",
        "features": observed_features(
            '<div style="display:none"><a href="/order-online">Order Online</a></div>', "pizza",
            "https://rival.example/",
        ),
    }
    visible_rival = {
        "name": "Published Rival",
        "features": observed_features(
            '<main><a href="/order-online">Order Online</a></main>', "pizza",
            "https://published.example/",
        ),
    }
    rows = compare_features(target, [hidden_rival, visible_rival])
    ordering = next(row for row in rows if row["feature"] == "online ordering")
    assert ordering["competitors_scanned"] == 2
    assert ordering["competitors_with_feature"] == ["Published Rival"]
    assert ordering["competitor_details"][0]["status"] == "not_observed_on_page"
    assert ordering["competitor_details"][1]["evidence_url"] == "https://published.example/"


def test_inline_visibility_is_checked_without_excluding_visible_sibling_text():
    page = ('<main><p style="display: inline">Catering for events</p>'
            '<p style="display : none ;">Order Online</p>'
            '<p style="visibility:visible">Local Delivery</p>'
            '<p aria-hidden="false">Menu</p></main>')
    findings = observed_features(page, "pizza")
    assert findings["online ordering"]["observed"] is False
    assert all(findings[name]["observed"] for name in ("catering", "delivery", "menu"))
