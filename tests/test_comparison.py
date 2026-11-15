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



def test_explicit_feature_denials_are_not_mistaken_for_competitive_advantages():
    page = """<main>
      <p>We do not offer online ordering or delivery.</p>
      <p>Our catering service is currently unavailable.</p>
      <p>There is no menu online yet.</p>
    </main>"""
    features = observed_features(page, "pizza", "https://pizza.example/")
    assert all(not item['observed'] for item in features.values())
    assert all(item['evidence_url'] is None for item in features.values())


def test_affirmative_link_survives_negative_different_service():
    page = """<main><p>We do not offer catering.</p>
      <a href="/order-online">Order Online</a><a href="/menu">View Menu</a>
      <p>Delivery currently not available.</p>
    </main>"""
    features = observed_features(page, "pizza", "https://pizza.example/")
    assert features['online ordering']['observed'] is True
    assert features['menu']['observed'] is True
    assert features['catering']['observed'] is False
    assert features['delivery']['observed'] is False


def test_denied_feature_url_with_negative_label_does_not_claim_availability():
    page = '<a href="/book-online">Online booking not available</a><p>We do not offer emergency service.</p>'
    features = observed_features(page, 'plumber', 'https://plumbing.example/')
    assert features['online booking']['observed'] is False
    assert features['emergency service']['observed'] is False



def test_external_and_query_only_paths_do_not_claim_competitor_checkout():
    page = """<main><p>Visit our local bakery.</p>
      <a href="https://partner.example/order-online">Partner information</a>
      <a href="/learn-more?next=/order-online">Learn more</a>
      <a href="/press#order-online">Press coverage</a>
    </main>"""
    observed = observed_features(page, "pizza", "https://bakery.example/")
    assert observed["online ordering"]["observed"] is False
    assert observed["online ordering"]["evidence_url"] is None


def test_visible_first_party_navigation_path_is_evidence_not_a_marketing_query():
    page = """<main><p>Our local kitchen.</p>
       <a href="https://www.pizza.example/order-online">Explore services</a>
       <a href="/menu">Browse our selections</a>
       <a href="/request?feature=catering">Ask a question</a>
    </main>"""
    observed = observed_features(page, "pizza", "https://pizza.example/")
    assert observed["online ordering"]["observed"] is True
    assert observed["menu"]["observed"] is True
    assert observed["catering"]["observed"] is False


def test_relative_path_allowed_without_a_known_source_but_external_links_are_not():
    no_origin = observed_features(
        '<a href="https://offsite.example/order-online">Partner</a>'
        '<a href="/order-online">Browse</a>', "pizza")
    assert no_origin["online ordering"]["observed"] is True
    outside_only = observed_features(
        '<a href="https://offsite.example/order-online">Partner</a>', "pizza")
    assert outside_only["online ordering"]["observed"] is False



def test_planned_or_coming_soon_features_are_not_current_competitor_advantages():
    from backend.comparison import affirmed_feature
    assert not affirmed_feature("Order online coming soon.", ("order online",))
    assert not affirmed_feature("Coming soon: order online.", ("order online",))
    assert not affirmed_feature("We plan to offer order online later.", ("order online",))
    assert not affirmed_feature("Financing will launch next month.", ("financing",))
    assert not affirmed_feature("Reservations launching soon.", ("reservations",))
    assert affirmed_feature("Order online now and collect at the counter.", ("order online",))
    assert affirmed_feature("Financing available today.", ("financing",))


def test_planned_ordering_does_not_create_a_fake_competitor_website_gap():
    target=observed_features("<main><h1>Local Pizza</h1></main>","pizza")
    planned=observed_features(
        "<main><h1>Coming soon: Order online</h1></main>","pizza","https://planned.example/")
    operating=observed_features(
        "<main><a href='/order-online'>Order online now</a></main>","pizza","https://operating.example/")
    assert planned["online ordering"]["observed"] is False
    assert operating["online ordering"]["observed"] is True
    rows=compare_features(target,[
        {"name":"Announced only","features":planned},
        {"name":"Operational","features":operating},
    ])
    ordering=next(x for x in rows if x["feature"]=="online ordering")
    assert ordering["competitors_with_feature"]==["Operational"]
