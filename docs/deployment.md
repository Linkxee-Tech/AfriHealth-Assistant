# Deployment Guide

## Local (development)
```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload &
cd frontend && streamlit run app.py
```

## Docker
```bash
docker-compose up --build
```
Ports: 8000 (API), 8501 (Streamlit)

## Connecting Frontend to Backend
In `frontend/config.py`, set:
```python
BACKEND_CONNECTED = True
BACKEND_BASE_URL = "http://localhost:8000"
```
