# Deployment Guide

## Local (development)
Start the backend from the repository root:

```bash
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

Start the frontend in a second terminal:

```bash
cd frontend
python -m streamlit run app.py
```

## Docker
```bash
docker-compose up --build
```
Ports: 8000 (API), 8501 (Streamlit). For a local non-container run, open
`http://127.0.0.1:8000/docs`; do not open `http://0.0.0.0:8000` in a browser.

The image excludes model binaries and generated vector data. Mount
`backend/models` and `backend/data` as configured in Compose, verify the local
embedding model exists, and build the knowledge base before production use.
The API reports stub mode when no compatible local LLM is mounted.

## Connecting Frontend to Backend
In the root `.env`, set:
```python
BACKEND_CONNECTED=True
BACKEND_BASE_URL=http://localhost:8000
```

For local development, the API accepts browser preflight requests from
`localhost` and `127.0.0.1` on any port. For production, set `ALLOWED_ORIGINS`
to the exact frontend origin(s) and clear `ALLOWED_ORIGIN_REGEX` to enforce
strict origin allowlisting.

The online API provides connectivity/search and an authenticated local JSON
backup. Cloud sync and telemedicine report unavailable until external
providers are configured; they do not return fake success responses.
