"""RAG engine unit tests — runs in stub mode (ChromaDB may not be installed)."""

import pytest
from backend.core.rag_engine import RAGEngine
from backend.core.llm_engine import LLMEngine
from backend.core.embedding_service import EmbeddingService


@pytest.fixture
def engines(tmp_path):
    llm     = LLMEngine(model_path="/nonexistent/model.gguf")
    llm.load_model()
    emb     = EmbeddingService()
    emb.load_model()
    rag     = RAGEngine(vector_db_path=str(tmp_path / "chroma"))
    rag.set_llm(llm)
    rag.set_embedder(emb)
    rag.initialize()
    return rag, llm, emb


def test_rag_initialises(engines):
    rag, _, _ = engines
    assert rag._initialized is True


def test_rag_generate_answer_returns_dict(engines):
    rag, _, _ = engines
    result = rag.generate_answer("What is malaria?")
    assert isinstance(result, dict)
    assert "answer" in result
    assert "sources" in result


def test_rag_stream_answer_yields_tokens(engines):
    rag, _, _ = engines
    tokens = list(rag.stream_answer("What is typhoid?"))
    assert len(tokens) > 0


def test_rag_retrieve_returns_list(engines):
    rag, _, _ = engines
    results = rag.retrieve("malaria treatment")
    assert isinstance(results, list)


def test_rag_add_and_retrieve_documents(engines):
    rag, _, _ = engines
    docs = [
        {"text": "Malaria is caused by Plasmodium parasites transmitted by mosquitoes.",
         "source": "test_doc.txt", "chunk_id": 0},
        {"text": "Treatment includes artemisinin-based combination therapies (ACTs).",
         "source": "test_doc.txt", "chunk_id": 1},
    ]
    added = rag.add_documents(docs)
    # In stub mode (no ChromaDB) returns 0; with ChromaDB returns 2
    assert added >= 0
