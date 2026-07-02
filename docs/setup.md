# Setup Instructions

## Prerequisites

- Python 3.10+
- 8 GB RAM minimum (16 GB recommended)
- 10 GB free disk space (for model + data)
- Linux / macOS / Windows (WSL2 recommended on Windows)

---

## Quick Start

### 1. Clone and install

```bash
git clone https://github.com/Linkxee-Tech/AfriHealth-Assistant.git
cd AfriHealth-Assistant
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Install llama-cpp-python (CPU build)

```bash
pip install llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu
```

### 3. Install RAG dependencies

```bash
pip install langchain langchain-community chromadb sentence-transformers
```

### 4. Install document processing

```bash
pip install pypdf python-docx easyocr
```

### 5. Download models

```bash
python scripts/download_models.py
```

### 6. Download medical datasets

```bash
python scripts/download_datasets.py
# Then add any additional PDFs to backend/data/raw_data/who_guidelines/ etc.
```

### 7. Build the knowledge base

```bash
python scripts/build_knowledge_base.py
```

### 8. Run the backend

```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
# Visit http://localhost:8000/docs for the interactive API docs
```

### 9. Run the frontend (separate terminal)

```bash
cd frontend
streamlit run app.py
# Visit http://localhost:8501
```

---

## Environment Variables

Copy `.env.example` to `.env` and adjust:

```bash
cp .env.example .env
```

Key variables:

| Variable | Default | Description |
|---|---|---|
| MODEL_PATH | backend/models/llm/llama-3-8b-q4.gguf | Path to GGUF model file |
| EMBEDDING_MODEL | backend/models/embedding/all-MiniLM-L6-v2 | Embedding model path |
| DB_PATH | backend/data/afrihealth.db | SQLite database path |
| VECTOR_DB_PATH | backend/data/vector_db/chroma_db | ChromaDB storage path |
| NUM_THREADS | 4 | CPU threads for inference |
| BACKEND_CONNECTED | False | Set True in frontend/config.py when backend is running |

---

## Running Tests

```bash
# Backend
pytest backend/tests/ -v

# Frontend
cd frontend && pytest tests/ -v
```
