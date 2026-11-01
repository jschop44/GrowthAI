"""Coordinated engines must share evidence without inventing unavailable facts."""
import backend.intelligence_team as team

def test_team_coordinates_independent_results(monkeypatch):
    monkeypatch.setattr(team, "run_public_intelligence", lambda url, cik: {
        "engines": {"pagespeed_mobile": {"status": "available", "source": "PageSpeed", "strategy": "mobile", "performance_score": 88},
                    "pagespeed_desktop": {"status": "unavailable", "source": "PageSpeed"},
                    "corporate_filings": {"status": "not_requested", "source": "SEC"}},
        "cache_hits": ["pagespeed_mobile"]})
    monkeypatch.setattr(team, "website_worker", lambda *args: {"status": "blocked", "source": "Target website"})
    monkeypatch.setattr(team, "discovery_worker", lambda *args: {"status": "unavailable", "source": "OSM"})
    result = team.run_team("https://example.com", None, 15, None, None, None, None, None)
    assert result["engines"]["website"]["status"] == "blocked"
    assert result["engines"]["pagespeed_mobile"]["performance_score"] == 88
    assert result["engines"]["opportunities"]["status"] == "unavailable"
    assert result["shared_evidence"]["public_provider_cache_hits"] == ["pagespeed_mobile"]

def test_team_route_requires_private_key():
    from fastapi.testclient import TestClient
    from backend.main import app
    response = TestClient(app).post("/api/intelligence-team", json={"url": "https://example.com"})
    assert response.status_code == 401

def test_discovery_with_blocked_website_and_explicit_industry(monkeypatch):
    class Client:
        def __init__(self, *args, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
    monkeypatch.setattr(team.httpx, "Client", Client)
    monkeypatch.setattr(team, "geocode", lambda client, identity: (39.5, -76.3, "user supplied address"))
    monkeypatch.setattr(team, "discover_competitors", lambda *args: ([{"name": "Pizza Example"}], None, "Geoapify + Overpass"))
    result = team.discovery_worker({"status": "blocked"}, "Bel Air, MD", 15, "pizza")
    assert result["status"] == "available"
    assert result["classification"]["confidence"] == "user-supplied"
    assert len(result["competitors"]) == 1
