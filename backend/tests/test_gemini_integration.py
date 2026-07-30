from backend.core.gemini_integration import GeminiIntegration


def test_gemini_unconfigured_status_is_explicit(monkeypatch):
    monkeypatch.setattr("backend.core.gemini_integration._GENAI_AVAILABLE", False)
    client = GeminiIntegration()
    assert client.get_status()["configured"] is False
    assert client.check_cost()["tokens_used"] == 0

