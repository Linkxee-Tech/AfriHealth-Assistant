"""LLM engine unit tests — run in stub mode (no model file required)."""

import pytest
from backend.core.llm_engine import LLMEngine


class _RecordingModel:
    def __init__(self):
        self.calls = []

    def __call__(self, prompt, **kwargs):
        self.calls.append((prompt, kwargs))
        return {"choices": [{"text": "ok"}]}


def test_llm_engine_instantiates():
    engine = LLMEngine()
    assert engine is not None


def test_stub_response_returned_when_model_absent():
    engine = LLMEngine(model_path="/nonexistent/model.gguf")
    engine.load_model()
    result = engine.generate("What is malaria?")
    assert isinstance(result, str)
    assert len(result) > 0


def test_stub_stream_yields_tokens():
    engine = LLMEngine(model_path="/nonexistent/model.gguf")
    engine.load_model()
    tokens = list(engine.stream_generate("What is typhoid?"))
    assert len(tokens) > 0
    full_text = "".join(tokens)
    assert len(full_text) > 10


def test_get_status_returns_dict():
    engine = LLMEngine(model_path="/nonexistent/model.gguf")
    engine.load_model()
    status = engine.get_status()
    assert "model_loaded" in status
    assert "memory_usage_gb" in status
    assert "cpu_percent" in status


def test_get_memory_usage_returns_float():
    engine = LLMEngine()
    mem = engine.get_memory_usage()
    assert isinstance(mem, float)
    assert mem >= 0.0


def test_generate_preserves_zero_temperature():
    engine = LLMEngine(model_path="/nonexistent/model.gguf")
    model = _RecordingModel()
    engine._model = model
    engine._loaded = True

    assert engine.generate("Test prompt", temperature=0.0) == "ok"
    assert model.calls[0][1]["temperature"] == 0.0
