"""Offline safety regressions for the public GrowthLens release probe."""
from scripts.verify_growthlens_release import ORIGIN, SHA_PATTERN, assess

EXPECTED = "a" * 40
OLDER = "b" * 40


def test_exact_live_revision_and_private_route_required():
    assert assess({"status": "ok", "release": EXPECTED}, EXPECTED, 401) == {
        "outcome": "verified_live",
        "expected_sha": EXPECTED,
        "live_sha": EXPECTED,
        "health": "ok",
        "private_audits_http_status": 401,
    }


def test_published_image_does_not_imply_live_render_deployment():
    result = assess({"status": "ok", "release": OLDER}, EXPECTED, 401)
    assert result["outcome"] == "stale_or_unidentified_render_image"
    assert result["live_sha"] == OLDER
    assert assess({"status": "ok", "release": None}, EXPECTED, 401)["outcome"] == "stale_or_unidentified_render_image"


def test_private_route_publicly_accessible_fails_even_with_matching_release():
    for http_code in (200, 302, 404, 503, None):
        result = assess({"status": "ok", "release": EXPECTED}, EXPECTED, http_code)
        assert result["outcome"] == "private_route_auth_unverified"


def test_healthy_service_required_and_non_sha_release_is_not_exposed():
    assert assess({"status": "error", "release": EXPECTED}, EXPECTED, 401)["outcome"] == "unhealthy"
    assert assess(None, EXPECTED, 401)["outcome"] == "unhealthy"
    invalid = assess({"status": "ok", "release": "untrusted data"}, EXPECTED, 401)
    assert invalid["outcome"] == "stale_or_unidentified_render_image"
    assert invalid["live_sha"] is None
    assert SHA_PATTERN.fullmatch(EXPECTED)
    assert ORIGIN == "https://growthlens-free-test.onrender.com"
