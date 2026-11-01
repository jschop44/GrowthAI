"""Independent providers must remain isolated and report partial failures."""
from backend.public_intelligence import run_public_intelligence, sec_worker
import backend.public_intelligence as intel

def test_parallel_results_and_source_accountability(monkeypatch):
    monkeypatch.setattr(intel, "pagespeed_worker", lambda url, strategy: {"status": "available" if strategy == "mobile" else "unavailable", "source": "Google PageSpeed Insights"})
    monkeypatch.setattr(intel, "sec_worker", lambda cik: {"status": "not_requested", "source": "SEC EDGAR"})
    result = run_public_intelligence("https://example.com")
    assert result["verified_sources"] == ["pagespeed_mobile"]
    assert result["engines"]["pagespeed_desktop"]["status"] == "unavailable"
    assert "No blocked website was crawled or bypassed." in result["limitations"]

def test_sec_cik_validation():
    assert sec_worker("not-a-cik")["status"] == "invalid"
    assert sec_worker(None)["status"] == "not_requested"

def test_private_route_requires_authentication():
    from backend.main import app
    from fastapi.testclient import TestClient
    response = TestClient(app).post("/api/public-intelligence", json={"url": "https://example.com"})
    assert response.status_code == 401
