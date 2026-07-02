# AfriHealth Assistant 🩺

**Intelligent Healthcare, Offline. For Africa.**

A 100% offline AI medical assistant built for the ADTC 2026 Challenge. It runs
entirely on standard laptop hardware (Intel i5 / Ryzen 5, 8GB RAM) with zero
reliance on cloud APIs, combining a locally quantised LLM with
retrieval-augmented generation over trusted medical sources.

## Project Status

| Part | Status |
|---|---|
| Frontend (Streamlit, multipage) | ✅ Built and verified |
| Backend (FastAPI + llama.cpp + RAG) | ⏳ Not yet built — frontend has stub fallbacks ready to swap in |

## Project Structure

```
AfriHealth-Assistant/
├── frontend/              # Streamlit multipage app (this build)
│   ├── app.py             # Landing page / entry point
│   ├── config.py          # Theme, constants, model setting defaults
│   ├── db.py               # Local SQLite persistence (chat history, health logs)
│   ├── pages/              # 1 Chat · 2 Health Metrics · 3 Document Analysis ·
│   │                        4 Chat History · 5 Settings · 6 About
│   ├── components/         # Reusable UI pieces (sidebar, chat, metrics, etc.)
│   ├── utils/               # api_client (backend seam), session_state, formatters
│   ├── assets/              # css/style.css, images/logo.png + favicon.ico
│   └── tests/               # pytest + Streamlit AppTest suite
├── backend/                 # FastAPI + llama.cpp + RAG (not yet implemented)
├── knowledge_base/          # RAG knowledge base builder (not yet implemented)
├── scripts/                 # Model download / benchmarking scripts (not yet implemented)
└── docs/                    # Architecture & setup docs (not yet implemented)
```

## Running the frontend

```bash
pip install -r requirements.txt
cd frontend
streamlit run app.py
```

Open the URL Streamlit prints (defaults to `http://localhost:8501`).

## Running the frontend tests

```bash
cd frontend
pytest tests/test_components.py -v
```

All 4 tests (landing boot, every page boots, chat send flow, health log entry)
pass as of this build.

## How the frontend talks to the backend (once it exists)

Every backend interaction goes through `frontend/utils/api_client.py`. Right
now `config.BACKEND_CONNECTED = False`, so every function falls back to local
SQLite / stub generators. Once FastAPI is running, flip that flag and each
function in `api_client.py` switches to real HTTP calls — no changes needed
in `pages/` or `components/`.

## Features implemented (frontend)

- 💬 **Chat** — multi-line input, prominent Send button, word-by-word
  streaming response rendering, source citation display, quick-question
  shortcuts, New Chat (archives to history), Export Report.
- 📊 **Health Metrics** — log Blood Pressure, Heart Rate, Blood Sugar,
  Weight, Temperature, SpO2, Sleep Hours; latest-reading cards; trend
  charts; date-range filter; CSV export; delete entries.
- 📁 **Document Analysis** — file uploader (image/PDF/docx/txt), processing
  status, extracted-text + AI-interpretation stub (OCR/RAG pending backend).
- 📋 **Chat History** — searchable list of archived conversations, load back
  into the active chat, delete, export all history.
- ⚙️ **Settings** — model parameters (temperature, max tokens, top-p, thread
  count), Dark/Light theme, language (English/Hausa/Swahili), data
  management (clear chat, delete all history, reset to defaults).
- 📖 **About** — project info, team/role split, tech stack, license.

## License

MIT — see [LICENSE](./LICENSE).
