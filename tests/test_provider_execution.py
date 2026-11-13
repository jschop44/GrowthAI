"""No external calls: exercise simultaneous requests and failure isolation."""
from threading import Event
import sqlite3
from backend.provider_execution import submit_provider
import backend.public_intelligence as intel


def test_simultaneous_provider_calls_share_one_operation_and_clear_after_failure():
    started, release = Event(), Event()
    calls = []

    def worker():
        calls.append(1)
        started.set()
        assert release.wait(3)
        raise ValueError("Provider failed")

    first = submit_provider("same-site", "test-engine", worker, ())
    assert started.wait(3)
    assert submit_provider("same-site", "test-engine", worker, ()) is first
    release.set()
    try:
        first.result(3)
    except ValueError:
        pass
    assert calls == [1]
    assert submit_provider("same-site", "test-engine", lambda: "recovered", ()).result(3) == "recovered"


def test_cache_failure_retains_live_provider_results(monkeypatch):
    def broken(*args):
        raise sqlite3.OperationalError("disk unavailable")
    monkeypatch.setattr(intel.evidence_registry, "get", broken)
    monkeypatch.setattr(intel.evidence_registry, "put", broken)
    monkeypatch.setattr(intel, "pagespeed_worker", lambda *a: {"status": "available", "source": "PageSpeed", "performance_score": 90})
    monkeypatch.setattr(intel, "crux_worker", lambda *a: {"status": "not_configured", "source": "CrUX"})
    monkeypatch.setattr(intel, "sec_worker", lambda *a: {"status": "not_requested", "source": "SEC"})
    monkeypatch.setattr(intel, "observatory_worker", lambda *a: {"status": "unavailable", "source": "MDN HTTP Observatory"})
    monkeypatch.setattr(intel, "html_checker_worker", lambda *a: {"status": "unavailable", "source": "W3C Nu HTML Checker"})
    result = intel.run_public_intelligence("https://example.com")
    assert result["engines"]["pagespeed_mobile"]["performance_score"] == 90
    assert result["verified_sources"] == ["pagespeed_mobile", "pagespeed_desktop"]


def test_one_worker_crash_does_not_discard_other_team_results(monkeypatch):
    import backend.intelligence_team as team
    monkeypatch.setattr(team, "website_worker", lambda *a: (_ for _ in ()).throw(RuntimeError("bad parser")))
    monkeypatch.setattr(team, "run_public_intelligence", lambda *a: {"engines": {"test": {"status": "available", "source": "Independent source"}}})
    monkeypatch.setattr(team.learning_engine, "recall", lambda *a: {})
    result = team.run_team("https://example.com", None, 15, None, None, None, None, None)
    assert result["engines"]["website"]["status"] == "unavailable"
    assert result["engines"]["test"]["status"] == "available"
    assert result["engines"]["opportunities"]["status"] == "unavailable"


def test_global_capacity_is_bounded_and_different_subjects_are_not_merged():
    from backend import provider_execution as execution
    release, started = Event(), Event()
    from threading import Lock
    lock = Lock()
    running = 0
    peak = 0

    def worker():
        nonlocal running, peak
        with lock:
            running += 1
            peak = max(peak, running)
            if running == 5:
                started.set()
        try:
            assert release.wait(3)
            return {"status": "available", "source": "test"}
        finally:
            with lock:
                running -= 1

    futures = []
    try:
        futures = [submit_provider("bounded-" + str(i), "test", worker, ()) for i in range(10)]
        assert started.wait(3)
        rejected = submit_provider("overflow", "test", worker, ()).result(1)
        assert rejected["status"] == "unavailable"
        assert "capacity" in rejected["reason"]
        assert len(set(futures)) == 10
    finally:
        release.set()
        for future in futures:
            future.result(3)
    assert peak == 5
    with execution._LOCK:
        assert not execution._PENDING
