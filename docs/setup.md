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
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
# Visit http://127.0.0.1:8000/docs for the interactive API docs

`0.0.0.0` is only a server bind address and must not be entered in a browser.
Use `127.0.0.1` or `localhost` for local URLs. Docker continues to bind the
container to `0.0.0.0` internally and is accessed through the published port.
```

### 9. Run the frontend (separate terminal)

```bash
cd frontend
.\venv\Scripts\Activate.ps1
python -m streamlit run app.py
# Visit http://localhost:8501
```

On Windows PowerShell, use the project environment explicitly:

```powershell
cd frontend
..\venv\Scripts\python.exe -m streamlit run app.py
```

The explicit project interpreter prevents an incompatible global Streamlit /
Starlette installation from being used.

---

## Environment Variables

Copy `.env.example` to `.env` and adjust:

```bash
cp .env.example .env
```

Key variables:

| Variable | Default | Description |
|---|---|---|
| MODEL_PATH | backend/models/llm/Llama-3.2-3B-Instruct-Q4_K_M.gguf | Path to the requested GGUF model file |
| EMBEDDING_MODEL | backend/models/embedding/all-MiniLM-L6-v2 | Embedding model path |
| DB_PATH | backend/data/afrihealth.db | SQLite database path, resolved from the project root |
| VECTOR_DB_PATH | backend/data/vector_db/chroma_db | ChromaDB storage path |
| NUM_THREADS | 4 | CPU threads for inference |
| BACKEND_CONNECTED | False | Set True in the root `.env` when the backend is running |
| ALLOWED_ORIGINS | localhost/127.0.0.1:8501 | Comma-separated exact browser origins |
| ALLOWED_ORIGIN_REGEX | local HTTP origins | Local development pattern; clear it for strict production allowlisting |

The checked-in embedding model is local and the knowledge-base builder stores
vectors in `backend/data/vector_db/chroma_db/`. `MODEL_PATH` must point to a
real llama.cpp-compatible GGUF file; a file with only a GGUF header is not
sufficient.

---

## Running Tests

```bash
# Backend
pytest backend/tests/ -v

# Frontend
cd frontend && pytest tests/ -v
```
## Password recovery

The backend exposes `POST /auth/forgot-password` and `POST /auth/reset-password`.

For an offline/local deployment, keep `AUTH_RECOVERY_MODE=local`: after submitting a registered username, the response contains an 8-character one-time recovery token. Use that token with `/auth/reset-password` and a new password. Tokens expire after `PASSWORD_RESET_TTL_MINUTES` and cannot be reused.

For production, set `AUTH_RECOVERY_MODE=email`, register users with an email address, and configure `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM`, and `SMTP_USE_TLS`. In email mode, tokens are not returned in the API response.

For an offline account that has no email, set a strong private `PASSWORD_RESET_ADMIN_TOKEN` and use `POST /auth/admin-recover`. Do not expose this token to regular users.
