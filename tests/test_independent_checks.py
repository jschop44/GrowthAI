"""Independent scanner integrations: isolate external claims and never guess a score."""
import pytest
import backend.independent_checks as checks
import backend.public_intelligence as intelligence


class FakeResponse:
    def __init__(self, data, status=200):
        self.data, self.status_code = data, status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise checks.httpx.HTTPStatusError("HTTP failure", request=checks.httpx.Request("GET", "https://example.org"), response=checks.httpx.Response(self.status_code))

    def json(self):
        return self.data


class FakeClient:
    calls = []
    payload = {}

    def __init__(self, *args, **kwargs):
        assert kwargs["trust_env"] is False
        assert kwargs["timeout"] <= 16

    def __enter__(self): return self
    def __exit__(self, *args): return False

    def post(self, endpoint, **kwargs):
        self.calls.append((endpoint, kwargs))
        return FakeResponse(self.payload)

    def get(self, endpoint, **kwargs):
        self.calls.append((endpoint, kwargs))
        return FakeResponse(self.payload)


def test_mdn_security_grade_is_from_actual_v2_response(monkeypatch):
    FakeClient.calls = []
    FakeClient.payload = {"grade": "B+", "score": 85, "tests_passed": 9, "tests_failed": 2, "scanned_at": "2026-11-12T00:00:00Z"}
    monkeypatch.setattr(checks.httpx, "Client", FakeClient)
    result = checks.observatory_worker("https://example.com/path?secret=do-not-send")
    assert result["status"] == "available"
    assert (result["grade"], result["tests_failed"]) == ("B+", 2)
    endpoint, options = FakeClient.calls[0]
    assert endpoint == "https://observatory-api.mdn.mozilla.net/api/v2/scan"
    assert options["params"] == {"host": "example.com"}
    assert "do-not-send" not in str(FakeClient.calls)


def test_incomplete_or_fake_security_grade_is_unavailable(monkeypatch):
    FakeClient.payload = {"grade": "A+", "score": None}
    monkeypatch.setattr(checks.httpx, "Client", FakeClient)
    assert checks.observatory_worker("https://example.com")["status"] == "unavailable"
    assert checks.observatory_worker("https://localhost/private")["status"] == "unavailable"


def test_w3c_checker_reports_observed_errors_without_a_synthetic_score(monkeypatch):
    FakeClient.calls = []
    FakeClient.payload = {"messages": [
        {"type": "error", "message": "Duplicate id", "lastLineNumber": 18},
        {"type": "info", "message": "Consider adding a heading"},
        {"type": "error", "message": "Unclosed element"},
    ]}
    monkeypatch.setattr(checks.httpx, "Client", FakeClient)
    result = checks.html_checker_worker("https://example.com/about?token=private")
    assert result["status"] == "available"
    assert result["markup_errors"] == 2
    assert result["markup_warnings"] == 1
    assert "score" not in result
    endpoint, options = FakeClient.calls[0]
    assert endpoint == "https://validator.w3.org/nu/"
    assert options["params"]["doc"] == "https://example.com/about"
    assert options["params"]["out"] == "json"
    assert "token=private" not in str(FakeClient.calls)


def test_w3c_validator_fatal_document_error_is_not_misreported_as_markup_failure(monkeypatch):
    FakeClient.payload = {"messages": [{"type": "non-document-error", "message": "Cannot retrieve URL"}]}
    monkeypatch.setattr(checks.httpx, "Client", FakeClient)
    assert checks.html_checker_worker("https://example.org")["status"] == "unavailable"


def test_on_demand_route_only_runs_the_two_independent_providers(monkeypatch, tmp_path):
    monkeypatch.setenv("GROWTHLENS_EVIDENCE_DB", str(tmp_path/"checks.sqlite"))
    monkeypatch.setattr(intelligence, "observatory_worker", lambda url: {"status": "available", "source": "MDN HTTP Observatory", "grade": "A", "score": 90})
    monkeypatch.setattr(intelligence, "html_checker_worker", lambda url: {"status": "available", "source": "W3C Nu HTML Checker", "markup_errors": 2})
    monkeypatch.setattr(intelligence, "pagespeed_worker", lambda *args: pytest.fail("PageSpeed must not run in checks-only mode"))
    monkeypatch.setattr(intelligence, "crux_worker", lambda *args: pytest.fail("CrUX must not run in checks-only mode"))
    monkeypatch.setattr(intelligence, "sec_worker", lambda *args: pytest.fail("SEC must not run in checks-only mode"))
    result = intelligence.run_public_intelligence("https://example.com", checks_only=True)
    assert set(result["engines"]) == {"http_security", "html_markup"}
    assert set(result["verified_sources"]) == {"http_security", "html_markup"}
    again = intelligence.run_public_intelligence("https://example.com", checks_only=True)
    assert set(again["cache_hits"]) == {"http_security", "html_markup"}


def test_checks_endpoint_stays_private():
    from fastapi.testclient import TestClient
    from backend.main import app
    response = TestClient(app).post("/api/website-checks", json={"url": "https://example.org"})
    assert response.status_code == 401
