import os
from backend import learning_engine

def test_deterministic_embedding_is_bounded(monkeypatch):
    monkeypatch.delenv("HF_TOKEN", raising=False)
    values, mode = learning_engine.vectorize("pizza restaurant website audit")
    assert mode == "deterministic"
    assert len(values) == 384

def test_local_memory_recall_and_source_requirement(tmp_path, monkeypatch):
    monkeypatch.setenv("GROWTHLENS_MEMORY_DB", str(tmp_path / "memory.db"))
    monkeypatch.delenv("QDRANT_URL", raising=False)
    monkeypatch.delenv("QDRANT_API_KEY", raising=False)
    monkeypatch.delenv("HF_TOKEN", raising=False)
    assert not learning_engine.store("https://example.com", "website", {"score": 80})["stored"]
    result = learning_engine.store("https://example.com", "website", {"source":"website", "score":80})
    assert result["stored"] and not result["persistent"]
    history = learning_engine.recall("https://example.com")
    assert len(history["observations"]) == 1
    assert history["observations"][0]["data"]["score"] == 80
    assert not history["observations"][0]["verified"]
