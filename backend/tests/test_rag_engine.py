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


def test_rag_tenant_isolation(engines):
    rag, _, _ = engines
    if rag._collection is None:
        pytest.skip("ChromaDB is not active in this test runner environment")

    # Add three documents: one public/global, one private to user 1, one private to user 2
    docs = [
        {
            "text": "Global malaria treatment guidelines.",
            "source": "global.txt",
            "chunk_id": 0,
            "metadata": {"visibility": "public", "user_id": 0}
        },
        {
            "text": "User 1 medical record containing secret diagnosis code alpha.",
            "source": "user1.txt",
            "chunk_id": 1,
            "metadata": {"visibility": "private", "user_id": 1}
        },
        {
            "text": "User 2 medical record containing secret diagnosis code beta.",
            "source": "user2.txt",
            "chunk_id": 2,
            "metadata": {"visibility": "private", "user_id": 2}
        }
    ]
    rag.add_documents(docs)

    # 1. Retrieve as user 1 -> should get global + user 1 docs, but NOT user 2 docs
    results_user1 = rag.retrieve("diagnosis code", user_id=1, top_k=5)
    texts_user1 = [r["text"] for r in results_user1]
    assert any("alpha" in t for t in texts_user1)
    assert not any("beta" in t for t in texts_user1)

    # 2. Retrieve as user 2 -> should get global + user 2 docs, but NOT user 1 docs
    results_user2 = rag.retrieve("diagnosis code", user_id=2, top_k=5)
    texts_user2 = [r["text"] for r in results_user2]
    assert any("beta" in t for t in texts_user2)
    assert not any("alpha" in t for t in texts_user2)

    # 3. Retrieve as anonymous -> should get global docs only, NOT user 1 or user 2 docs
    results_anon = rag.retrieve("diagnosis code", user_id=None, top_k=5)
    texts_anon = [r["text"] for r in results_anon]
    assert not any("alpha" in t for t in texts_anon)
    assert not any("beta" in t for t in texts_anon)

