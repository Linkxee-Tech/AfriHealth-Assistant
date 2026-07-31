from backend.core.hybrid_orchestrator import HybridOrchestrator


def test_hybrid_aliases_and_cache(monkeypatch):
    orchestrator = HybridOrchestrator()
    monkeypatch.setattr(orchestrator, "is_online", lambda: False)
    monkeypatch.setattr(
        orchestrator.rag_engine,
        "retrieve",
        lambda query, top_k=3, user_id=None: [{"source": "WHO", "text": "malaria"}],
    )
    first = orchestrator.process_query("malaria")
    second = orchestrator.process_query("malaria")
    assert first["mode"] == "OFFLINE"
    assert second["cached"] is True
    assert orchestrator.decide_mode("hello") == "OFFLINE"
