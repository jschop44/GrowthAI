"""Offline end-to-end HTTP contract tests for local competitor intelligence."""
import json
import os
from fastapi.testclient import TestClient
from fastapi import FastAPI
from backend import main
from backend import local_competition as local

TARGET = """<html><head><title>Sample Roofing</title>
<script type="application/ld+json">{"@context":"https://schema.org","@type":"RoofingContractor","name":"Sample Roofing","geo":{"latitude":39.5,"longitude":-76.3}}</script>
</head><body><h1>Sample Roofing</h1><p>Roof repairs and replacement</p></body></html>"""
RIVAL = "<html><head><title>Nearby Roofer</title></head><body><h1>Nearby Roofer</h1><p>Financing available. Request a quote.</p></body></html>"

def test_local_http_report_with_competitor_evidence(monkeypatch):
    monkeypatch.setenv("GROWTHLENS_PRIVATE_KEY", "testing-secret")
    monkeypatch.setattr(main.socket, "getaddrinfo", lambda *args, **kwargs: [(2, 1, 6, "", ("93.184.215.14", 0))])
    # Register the production route against isolated, deterministic network dependencies.
    class FakeResponse:
        def __init__(self, text):
            self.text = text
    fake_fetch = lambda client, url: (FakeResponse(RIVAL if "rival" in url else TARGET), url)
    monkeypatch.setattr(local, "geocode", lambda client, identity: (39.5, -76.3, "structured data"))
    monkeypatch.setattr(local, "osm_competitors", lambda *args: ([{"name":"Nearby Roofer","website":"https://rival.example","distance_miles":2.0,"match_reason":"matching category"}],None))
    isolated = FastAPI()
    local.register_local_routes(isolated, lambda url: url, fake_fetch, lambda client, url: True, main.analyze_html)
    response = TestClient(isolated).post("/api/local-competition",json={"url":"https://target.example","radius_miles":15})
    assert response.status_code == 200, response.text
    report = response.json()
    assert report["radius_miles"] == 15
    assert report["competitors"][0]["status"] == "audited"
    financing = next(row for row in report["feature_comparison"] if row["feature"] == "financing")
    assert financing["target_observed"] is False
    assert financing["competitors_with_feature"] == ["Nearby Roofer"]
    assert report["financial_scenarios"]["status"] == "illustrative"
    assert report["financial_scenarios"]["opportunities"][0]["confidence"] == "very low"
    assert report["revenue"]["amount"] is None

def test_private_api_denies_missing_key(monkeypatch):
    monkeypatch.setenv("GROWTHLENS_PRIVATE_KEY", "testing-secret")
    response = TestClient(main.app).post("/api/local-competition",json={"url":"https://target.example","radius_miles":15})
    assert response.status_code == 401

def test_invalid_radius_rejected_before_network(monkeypatch):
    monkeypatch.setenv("GROWTHLENS_PRIVATE_KEY", "testing-secret")
    response = TestClient(main.app).post("/api/local-competition",headers={"X-GrowthLens-Key":"testing-secret"},json={"url":"https://target.example","radius_miles":500})
    assert response.status_code == 422


def test_franchise_locations_reuse_one_website_audit_and_leave_budget_for_other_peers(monkeypatch):
    """Keep all physical store rows, but audit shared company pages only once."""
    from collections import Counter
    monkeypatch.setenv('GROWTHLENS_PRIVATE_KEY', 'testing-secret')
    calls = Counter()
    def fake_fetch(client, website):
        calls[website] += 1
        return type('Response', (), {'text': RIVAL if 'rival' in website or 'another' in website else TARGET})(), website
    branches = [
        {'name':f'Nearby Roofer branch {i}', 'website':'https://rival.example/',
         'distance_miles':float(i+1), 'lat':39.5+i*.001, 'lon':-76.3}
        for i in range(5)
    ]
    branches.append({'name':'Another Roofer','website':'https://another.example/',
                     'distance_miles':7.0,'lat':39.51,'lon':-76.31})
    monkeypatch.setattr(local, 'geocode', lambda *_: (39.5,-76.3,'structured data'))
    monkeypatch.setattr(local, 'discover_competitors',lambda *_: (branches,None,'offline test sources'))
    isolated = FastAPI()
    local.register_local_routes(isolated,lambda url:url,fake_fetch,lambda *_:True,main.analyze_html)
    response = TestClient(isolated).post('/api/local-competition',
                json={'url':'https://target.example/','radius_miles':15})
    assert response.status_code == 200,response.text
    report = response.json()
    assert len(report['competitors']) == 6,'All physical branches must remain in the listing'
    assert all(c['status']=='audited' for c in report['competitors'])
    assert calls['https://rival.example/'] == 1,'Shared homepage must not consume five free audits'
    assert calls['https://another.example/'] == 1,'An independent sixth listing still gets an audit'
    financing = next(row for row in report['feature_comparison'] if row['feature']=='financing')
    assert financing['competitors_scanned'] == 2,'Independent website sample must not count chain branches repeatedly'
    assert len(financing['competitors_with_feature']) == 2
    contact = next(f for f in report['audit']['findings'] if f['id']=='contact')
    assert contact['local_peer_comparison']['eligible_listing_count'] >= 2
    assert contact['local_peer_comparison']['sample_size'] <= 2
