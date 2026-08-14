# AfriHealth Assistant

**Intelligent Healthcare, Offline. For Africa.**

AfriHealth Assistant is a local-first healthcare assistant for the ADTC 2026 Challenge. It combines a Streamlit interface, a FastAPI backend, SQLite persistence, a local LLM/RAG pipeline, document processing, and optional online search or Gemini fallback.

## Current implementation status

The repository contains both the frontend and backend. Core local workflows
are wired and tested; release deployment still requires a compatible local LLM
GGUF and any external providers that the deployment chooses to enable.

| Area | Current state |
|---|---|
| Streamlit frontend | Eight page files are present, including Patients and Clinical Support. |
| FastAPI backend | Routes, authentication, services, database models, LLM, RAG, OCR, and hybrid modules are present. |
| Local AI | The local embedding model loads successfully; llama.cpp reports an explicit stub state until a compatible GGUF is mounted. |
| Knowledge base | 7 source PDFs produce 8,932 chunks and 8,932 stored Chroma vectors; retrieval was verified against malaria guidance. |
| Online/hybrid mode | Connectivity/search and Gemini fallback are implemented; authenticated local backup is real. Cloud sync and telemedicine correctly report unavailable until configured. |
| Tests | Backend: 39 passed. Frontend: 8 passed. The project virtual environment has no broken requirements. |

## Project structure

```text
AfriHealth-Assistant/
├── backend/
│   ├── api/             FastAPI routes, request/response models, auth dependencies
│   ├── core/            LLM, RAG, embeddings, OCR, document, health, and hybrid engines
│   ├── database/        SQLAlchemy models, manager, and migration files
│   ├── services/        Chat, history, document, patient, clinical, and settings services
│   ├── data/raw_data/   Medical source documents used to build the knowledge base
│   └── tests/            Backend tests
├── frontend/
│   ├── app.py           Streamlit landing/login page
│   ├── pages/           Chat, metrics, documents, history, patients, clinical support, settings, about
│   ├── components/      Reusable UI components
│   ├── utils/            API client, session state, formatters, and translations
│   ├── assets/           CSS, logos, favicon, and backgrounds
│   └── tests/            Streamlit tests
├── knowledge_base/      Dataset loading, chunking, embedding, and vector storage
├── scripts/             Model, dataset, knowledge-base, benchmark, and maintenance scripts
├── docs/                Setup, architecture, API, testing, deployment, and user documentation
├── models/              Project model storage location
├── submission/          Gate 1 and final submission materials
├── requirements.txt     Root backend/frontend dependency set
├── frontend/requirements.txt
├── .env.example         Environment variable template
├── Dockerfile
└── docker-compose.yml
```

## Setup from the project root

Use the repository root as the working directory:

```bash
cd AfriHealth-Assistant
python -m venv venv
```

Windows PowerShell:

```powershell
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

macOS/Linux:

```bash
source venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Copy `.env.example` to `.env` and set local paths and secrets as needed. Do
not commit `.env` or a real Gemini API key. The backend configuration defaults
to local storage under `backend/data/`; the frontend-only fallback uses its
local SQLite database under `frontend/`.

## Build the knowledge base

Place supported medical documents in the appropriate directories under
`backend/data/raw_data/`, then run this command from the project root:

```bash
python scripts/build_knowledge_base.py
```

To clear and rebuild the ChromaDB collection:

```bash
python scripts/build_knowledge_base.py --clear
```

The builder extracts text, splits it into overlapping chunks, generates
embeddings, and stores the vectors under `backend/data/vector_db/chroma_db/`.

## Run the application

### Important: LLM Configuration

**For online deployment**, you don't need to download the GGUF model. Instead, use a free cloud API:

- **Recommended**: [Groq](https://groq.com) (free, fast, no credit card)
- **Alternative**: [Hugging Face Inference API](https://huggingface.co)
- **Optional**: [Google Gemini](https://ai.google.dev)

See [DEPLOYMENT_ONLINE.md](DEPLOYMENT_ONLINE.md) for complete setup instructions.

### Running the Backend

Start the backend from the project root in one terminal:

```bash
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

The current backend registers routes at the root, so the basic checks are:

```text
http://127.0.0.1:8000/health
http://127.0.0.1:8000/status
http://127.0.0.1:8000/docs
```

### Running the Frontend

Start the frontend in a second terminal:

```bash
cd frontend
python -m streamlit run app.py
```

On Windows PowerShell, run the project interpreter explicitly if the virtual
environment is not activated:

```powershell
cd frontend
..\venv\Scripts\python.exe -m streamlit run app.py
```

This avoids pairing the global Streamlit installation with an older global
Starlette package.

Open `http://localhost:8501`. Register an account on the landing page, then
use the authenticated pages. The frontend/backend API seam is
`frontend/utils/api_client.py`.

## Frontend pages

1. Chat
2. Health Metrics
3. Documents
4. History
5. Patients
6. Clinical Support
7. Settings
8. About

## Backend capabilities

The backend currently contains these route groups:

- `/auth` — registration, login, and current-user lookup.
- `/health` and `/status` — process and model status.
- `/chat` and `/chat/history` — blocking/streaming chat and saved conversations.
- `/metrics` — health readings, vital checks, symptom analysis, coaching, and protocols.
- `/documents` — document upload, processing, analysis, and listing.
- `/patients` and `/visits` — patient and visit records.
- `/clinical` — guidelines, drugs, interactions, protocols, CDS, and triage.
- `/online` — connectivity, search, authenticated local JSON backup, provider status, and Gemini test endpoint.
- `/settings` — authenticated per-user settings persisted in SQLite.

All protected routes require a JWT bearer token obtained from `/auth/login` or
`/auth/register`.

Password recovery is available at `/auth/forgot-password` and
`/auth/reset-password`. Offline deployments use an expiring one-time local
token (`AUTH_RECOVERY_MODE=local`); production deployments should configure
SMTP and use `AUTH_RECOVERY_MODE=email` so reset tokens are delivered privately.

## Wiring fixes completed in this pass

- Standardized the active API contract on root routes such as `/health`,
  `/chat`, and `/metrics`; updated tests, Docker health checks, and API docs.
- Fixed the duplicated health `/metrics` prefix and OAuth2 login URL.
- Added authenticated ownership checks for conversations, metrics, and
  documents, and made database migrations explicit and observable.
- Corrected TXT/image document extraction, RAG chunk metadata, patient document
  persistence, and document-analysis retry behavior.
- Replaced broken page-level patient HTTP/database calls with API-client calls
  and fixed the undefined visit examination value without changing the form
  layout.
- Made frontend backend URL and connection state read from `.env`, aligned the
  Gemini dependency name, and prevented `.env` secrets from entering Docker
  images.
- Reconciled the frontend smoke tests with the current eight-page application.
- Added the missing patient search/export and visit-update API contracts, fixed
  clinical 400-error propagation, and normalised local/backend history records.
- Updated local model loading diagnostics and verified the configured GGUF path
  is checked at startup; the backend reports a clear load error and stub mode
  until a valid compatible GGUF is supplied.
- Removed dummy medical-data fallbacks, reconciled the model downloader so it
  cannot save TinyLlama under a Llama filename, and added GGUF validation.
- Replaced fake sync/telemedicine success responses with explicit provider
  availability responses; added a real authenticated user backup download.
- Wired settings persistence, destructive data-management actions, and patient
  PDF export without changing the existing page layout.
- Added an Alembic configuration and initial schema revision for fresh installs.

## Release blockers and optional provider work

1. Place the requested `Llama-3.2-3B-Instruct-Q4_K_M.gguf` at
   `backend/models/llm/Llama-3.2-3B-Instruct-Q4_K_M.gguf` and verify local
   generation on the deployment machine. The repository is wired for this
   path but the binary is intentionally not included or downloaded here.
2. Configure and security-review Gemini, cloud synchronization, and any
   telemedicine provider before enabling those optional features.
3. Clinical guideline and drug reference tables are seeded from source-labelled
   local references; qualified clinical review remains required before clinical deployment.
4. Keep the planned online/offline hybrid modification as a separate change;
   this verification pass preserved its existing decision logic.

## Checklist coverage

The supplied professional checklist declares 328 verification items, but its
unique identifiers enumerate 524 checks. The repository verification report
documents this discrepancy rather than silently treating the counts as equal.

- repository/setup and project structure;
- frontend pages and reusable components;
- backend routes, models, core engines, services, database, and utilities;
- frontend/backend integration and data flow;
- knowledge-base construction and RAG quality;
- medical safety and clinical support;
- online/offline hybrid mode and Gemini integration;
- performance and optimization;
- unit/integration testing;
- documentation, submission, and deployment.

The checklist is the verification plan for this repository. Its model references
“Gemini 3 Pro” must also be reconciled with the current code, which currently
uses the configured Google GenAI model and explicit availability/error reporting.

## Tests

Backend tests:

```bash
venv/Scripts/python -m pytest backend/tests -q
```

Frontend tests:

```bash
cd frontend
../venv/Scripts/python -m pytest tests -q
```

The test suite uses isolated model/database settings and can run without loading
the developer's local GGUF model or production vector store. The frontend tests
target the current eight-page application.

## Docker

The repository includes `Dockerfile` and `docker-compose.yml` for the optional
combined deployment. Verify the mounted models/data volumes and run the
knowledge-base build before production startup.

## Documentation

- [Setup](docs/setup.md)
- [Architecture](docs/architecture.md)
- [API reference](docs/api_reference.md)
- [Testing](docs/testing.md)
- [Deployment](docs/deployment.md)
- [User manual](docs/user_manual.md)

## License

MIT — see [LICENSE](LICENSE).
