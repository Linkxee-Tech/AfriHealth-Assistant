# AfriHealth Assistant — System Architecture

## Overview

AfriHealth Assistant is a **100% offline** AI medical assistant built on a
layered architecture ensuring modularity, maintainability, and high performance
on standard laptop hardware (Intel i5 / Ryzen 5, 8GB RAM).

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER (Browser)                           │
└───────────────────────────┬─────────────────────────────────────┘
                            │ HTTP
┌───────────────────────────▼─────────────────────────────────────┐
│              FRONTEND  (Streamlit :8501)                         │
│  pages/  │  components/  │  utils/api_client.py (seam)          │
└───────────────────────────┬─────────────────────────────────────┘
                            │ REST + SSE streaming
┌───────────────────────────▼─────────────────────────────────────┐
│              BACKEND  (FastAPI :8000)                            │
│                                                                  │
│  api/routes/   ← Blueprint (APIRouter) pattern                  │
│    chat.py     history.py   health.py   documents.py  system.py │
│                                                                  │
│  services/  (business logic)                                     │
│    chat_service  history_service  document_service               │
│                                                                  │
│  core/  (AI engines)                                             │
│    llm_engine ──► llama.cpp ──► Llama-3.2-3B-Instruct Q4 (.gguf)│
│    rag_engine ──► ChromaDB  ──► vector_db/                      │
│    embedding_service ──► all-MiniLM-L6-v2                       │
│    document_processor ──► easyOCR / pypdf / python-docx         │
│    health_analyzer ──► rule-based vitals triage                  │
│                                                                  │
│  database/  (SQLAlchemy + SQLite)                                │
│    conversations │ messages │ health_metrics │ documents         │
└─────────────────────────────────────────────────────────────────┘
                            │ all local disk I/O
┌───────────────────────────▼─────────────────────────────────────┐
│                    LOCAL STORAGE                                  │
│  afrihealth.db (SQLite)  │  chroma_db/ (vectors)                │
│  models/llm/*.gguf       │  models/embedding/                   │
│  data/raw_data/          │  data/processed_data/                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Key Design Decisions

| Decision | Choice | Reason |
|---|---|---|
| LLM runtime | llama.cpp | Optimised for CPU-only inference with 4-bit GGUF models |
| Model | Llama-3.2-3B-Instruct Q4_K_M | Local instruction model; supplied separately |
| Vector DB | ChromaDB (local) | Embeddable, no extra services, pure Python |
| Embeddings | all-MiniLM-L6-v2 | 384-dim, fast on CPU, excellent semantic quality |
| RAG framework | LangChain | Industry-standard tooling for chunking and retrieval |
| DB | SQLite via SQLAlchemy | Zero-config, single-file, fully offline |
| Frontend | Streamlit | Rapid iteration, Python-native, data-app focused |
| API | FastAPI + APIRouter | High-performance async, blueprint-style routing |

---

## Request Flow — Chat

```
User types query
      ↓
Streamlit (api_client.py) → POST /chat/stream
      ↓
chat_router → chat_service.stream_response()
      ↓
rag_engine.stream_answer()
      ↓
  ┌── embedding_service.embed(query)
  ├── chromadb.collection.query() → top-k chunks
  └── build_rag_prompt(query, context)
      ↓
llm_engine.stream_generate(prompt) → yields tokens
      ↓
FastAPI StreamingResponse → Streamlit renders word-by-word
```

---

## Data Model

See `backend/database/models.py` for full SQLAlchemy definitions.

| Table | Key columns |
|---|---|
| conversations | id, session_id, topic, started_at |
| messages | id, conversation_id, role, content, sources |
| health_metrics | id, metric_type, value, unit, notes, recorded_at |
| documents | id, filename, file_type, content, analysis_result |
