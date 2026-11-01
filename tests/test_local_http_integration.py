"""Offline end-to-end HTTP contract tests for local competitor intelligence."""
import json
import os
from fastapi.testclient import TestClient
from backend import main
from backend import local_competition as local

TARGET = """<html><head><title>Sample Roofing</title>
<script type="application/ld+json">{"@context":"https://schema.org","@type":"RoofingContractor","name":"Sample Roofing","geo":{"latitude":39.5,"longitude":-76.3}}</script>
</head><body><h1>Sample Roofing</h1><p>Roof repairs and replacement</p></body></html>"""
RIVAL = "<html><head><title>Nearby Roofer</title></head><body><h1>Nearby Roofer</h1><p>Financing available. Request a quote.</p></body></html>"

def test_local_http_report_with_competitor_evidence(monkeypatch):
    monkeypatch.setenv("GROWTHLENS_PRIVATE_KEY", "testing-secret")
    monkeypatch.setattr(main, "validate_url", lambda url: url)
    monkeypatch.setattr(main, "robots_allowed", lambda client, url: True)
    class FakeResponse:
        def __init__(self, text):
            self.text = text
    monkeypatch.setattr(main, "fetch_public", lambda client, url: (FakeResponse(RIVAL if "rival" in url else TARGET), url))
    monkeypatch.setattr(local, "geocode", lambda client, identity: (39.5, -76.3, "structured data"))
    monkeypatch.setattr(local, "osm_competitors", lambda *args: ([{"name":"Nearby Roofer","website":"https://rival.example","distance_miles":2.0,"match_reason":"matching category"}],None))
    response = TestClient(main.app).post("/api/local-competition",headers={"X-GrowthLens-Key":"testing-secret"},json={"url":"https://target.example","radius_miles":15})
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
