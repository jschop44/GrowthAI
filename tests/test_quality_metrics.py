import os
os.environ.setdefault('GROWTHLENS_PRIVATE_KEY', 'test-private-key')
from backend.main import analyze_html
from backend.quality_metrics import local_peer_evidence


def test_measured_security_and_visual_delivery_indicators():
    html = '''<html><head><script src="http://cdn.example/script.js"></script></head><body>
    <img src="/hero.jpg"><img src="/decor.jpg" alt="" width="100" height="100">
    <form action="http://example.com/submit"></form><a href="/contact"></a>
    <script type="application/ld+json">{broken</script></body></html>'''
    r = analyze_html(html, 'https://example.com/', 10)
    f = {x['id']: x for x in r['findings']}
    assert r['observations']['images_without_intrinsic_dimensions'] == 1
    assert r['observations']['images_missing_alt'] == 1
    for key in ('image_dimensions', 'blocking_scripts', 'mixed_content', 'secure_forms', 'schema_validity', 'accessible_links', 'main_landmark'):
        assert f[key]['passed'] is False
        assert f[key]['evidence']['source_url'] == 'https://example.com/'
        assert f[key]['cost_savings']['annual_usd'] is None
    assert r['measurement_coverage']['visual_design_quality'] == 'not_measured'
    assert sum(x['checks'] for x in r['category_metrics']) == len(r['findings'])


def test_decorative_images_pass_without_claiming_savings():
    r = analyze_html('<html><main><img src="decor.jpg" alt="" width="10" height="20"></main></html>', 'https://example.com/', 2)
    finding = next(f for f in r['findings'] if f['id'] == 'image_alt')
    assert finding['passed'] is True
    assert finding['financial_scenario']['annual_operating_savings_usd'] == 0
    assert r['observations']['decorative_images'] == 1


def test_valid_deferred_html_and_external_resource_counts():
    r = analyze_html('''<html><head><script src="https://cdn.example/app.js" defer></script></head><main>
    <a href="/contact" aria-label="Contact"></a><script type="application/ld+json">{"@type":"Organization"}</script>
    </main></html>''', 'https://example.com/', 3)
    f = {x['id']: x for x in r['findings']}
    assert all(f[k]['passed'] for k in ('blocking_scripts', 'schema_validity', 'accessible_links', 'main_landmark'))
    assert r['observations']['external_script_count'] == 1
    assert r['score'] <= 100


def test_peer_prevalence_excludes_unavailable_distant_and_unmeasured_sites():
    findings = [{'id': 'contact', 'passed': False}]
    peers = [{'name': 'Local', 'status': 'audited', 'distance_miles': 2, 'website': 'https://local.example', 'findings': [{'id': 'contact', 'passed': True}]},
             {'name': 'Far', 'status': 'audited', 'distance_miles': 60, 'findings': [{'id': 'contact', 'passed': True}]},
             {'name': 'Blocked', 'status': 'blocked', 'distance_miles': 1},
             {'name': 'No evidence', 'status': 'audited', 'distance_miles': 1, 'findings': []}]
    peers.append({'name':'Wrong niche','status':'audited','distance_miles':1,'peer_eligible':False,'website':'https://unrelated.example','findings':[{'id':'contact','passed':True}]})
    local_peer_evidence(findings, peers, 'dentist', 15)
    comparison = findings[0]['local_peer_comparison']
    assert comparison['sample_size'] == comparison['passing_count'] == 1
    assert comparison['sources'][0]['url'] == 'https://local.example'
    assert findings[0]['cost_savings']['annual_usd'] is None
    assert comparison['industry'] == 'dentist'


def test_security_failures_reach_explanations_and_shared_outreach_ranking(monkeypatch):
    from backend.main import fallback_explanation, shared_opportunity_score, OpportunityScoreRequest
    from backend import learning_engine
    monkeypatch.setattr(learning_engine, 'recall', lambda *args, **kwargs: {'observations': []})
    report = analyze_html('<html><form action="http://example.com/send"></form></html>', 'https://example.com/', 2)
    explanation = fallback_explanation(report)
    assert explanation.startswith('1. Secure form destinations')
    ranking = shared_opportunity_score(OpportunityScoreRequest(website='https://example.com/', findings=report['findings']))['ranking']
    assert ranking[0]['finding_id'] == 'secure_forms'
    assert 'main_landmark' in [item['finding_id'] for item in ranking]
    # Passing checks must not become outreach opportunities.
    assert 'mixed_content' not in [item['finding_id'] for item in ranking]


def test_security_order_survives_negative_user_reported_feedback(monkeypatch):
    from backend.main import shared_opportunity_score, OpportunityScoreRequest
    from backend import learning_engine
    monkeypatch.setattr(learning_engine, 'recall', lambda *args, **kwargs: {'observations': [
        {'kind': 'recommendation_outcome', 'data': {'recommendation_id': 'mixed_content', 'improved': False}}
        for _ in range(25)]})
    result = shared_opportunity_score(OpportunityScoreRequest(website='https://example.com/', platform='shopify', findings=[
        {'id': 'contact', 'passed': False}, {'id': 'lead_capture', 'passed': False},
        {'id': 'mixed_content', 'passed': False}, {'id': 'image_dimensions', 'passed': False}]))
    assert result['ranking'][0]['finding_id'] == 'mixed_content'


def test_chain_branches_cannot_inflate_independent_website_prevalence():
    findings = [{'id':'contact','passed':False}]
    peers = [
        {'name':'Chain North','website':'https://chain.example/','status':'audited','peer_eligible':True,
         'distance_miles':2,'findings':[{'id':'contact','passed':True}]},
        {'name':'Chain South','website':'https://www.chain.example/','status':'audited','peer_eligible':True,
         'distance_miles':4,'findings':[{'id':'contact','passed':True}]},
        {'name':'Independent','website':'https://independent.example/','status':'audited','peer_eligible':True,
         'distance_miles':3,'findings':[{'id':'contact','passed':False}]},
    ]
    local_peer_evidence(findings,peers,'roofing',15)
    result=findings[0]['local_peer_comparison']
    assert result['eligible_listing_count'] == 3
    assert result['duplicate_page_listings_excluded'] == 1
    assert result['sample_size'] == 2
    assert result['passing_count'] == 1
    assert len(result['sources']) == 2
    assert 'not independent' in result['note']



def test_hidden_template_and_css_invisible_images_do_not_inflate_visual_findings():
    html = '''<html><body><main>
      <template><img src="/template.jpg"></template>
      <noscript><img src="/noscript.jpg"></noscript>
      <div hidden><img src="/hidden-ancestor.jpg"></div>
      <div style="display : none !important"><img src="/hidden-style.jpg"></div>
      <section style="visibility: hidden"><img src="/invisible.jpg"></section>
      <img src="/pixel.gif" width="1" height="1">
      <img src="/visible.jpg" alt="A genuine product photograph" width="1200" height="800">
    </main></body></html>'''
    report = analyze_html(html, 'https://example.com/', 7)
    findings = {item['id']: item for item in report['findings']}
    assert report['observations']['images_missing_alt'] == 0
    assert report['observations']['images_without_intrinsic_dimensions'] == 0
    assert findings['image_alt']['passed'] is True
    assert findings['image_dimensions']['passed'] is True


def test_visible_undimensioned_image_still_has_real_audit_findings():
    html = '''<html><body><main>
       <section style="display:block"><img src="/visible.jpg"></section>
       <aside style="display:none"><img src="/not-rendered.jpg"></aside>
    </main></body></html>'''
    report = analyze_html(html, 'https://example.com/', 3)
    assert report['observations']['images_missing_alt'] == 1
    assert report['observations']['images_without_intrinsic_dimensions'] == 1
