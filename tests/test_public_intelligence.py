"""Independent providers must remain isolated and report partial failures."""
from backend.public_intelligence import run_public_intelligence, sec_worker
import backend.public_intelligence as intel

def test_parallel_results_and_source_accountability(monkeypatch):
    monkeypatch.setattr(intel.evidence_registry, "get", lambda subject, engine: None)
    monkeypatch.setattr(intel.evidence_registry, "put", lambda subject, engine, result: True)
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

def test_evidence_registry_cache_and_conflicts(monkeypatch, tmp_path):
    from backend import evidence_registry as registry
    monkeypatch.setenv("GROWTHLENS_EVIDENCE_DB", str(tmp_path / "evidence.sqlite"))
    first = {"status": "available", "source": "test-provider", "strategy": "mobile", "performance_score": 70}
    second = {"status": "available", "source": "other-provider", "strategy": "mobile", "performance_score": 82}
    assert registry.put("https://example.com", "mobile", first)
    assert registry.get("https://example.com", "mobile") == first
    assert registry.get("https://example.com", "desktop") is None
    assert not registry.put("https://example.com", "unavailable", {"status": "unavailable", "source": "test"})
    result = registry.reconcile({"a": first, "b": second})
    assert len(result["conflicts"]) == 1
    assert result["conflicts"][0]["status"] == "requires_review"
