@echo off
title AfriHealth Assistant — Launcher
cd /d "%~dp0"

echo ============================================================
echo  AfriHealth Assistant — Starting Up
echo ============================================================
echo.

REM ── 1. Start the FastAPI backend in a new window ─────────────
echo [1/2] Starting Backend (FastAPI on port 8000)...
start "AfriHealth Backend" cmd /k "cd /d "%~dp0" && venv\Scripts\uvicorn.exe backend.main:app --host 127.0.0.1 --port 8000 --reload"

REM ── 2. Wait a moment for backend to be ready ─────────────────
echo     Waiting 5 seconds for backend to initialise...
timeout /t 5 /nobreak >nul

REM ── 3. Start the Streamlit frontend in a new window ──────────
echo [2/2] Starting Frontend (Streamlit on port 8501)...
start "AfriHealth Frontend" cmd /k "cd /d "%~dp0" && venv\Scripts\streamlit.exe run frontend\app.py --server.port 8501 --server.address localhost"

echo.
echo ============================================================
echo  AfriHealth Assistant is running!
echo.
echo  Frontend : http://localhost:8501
echo  Backend  : http://localhost:8000
echo  API Docs : http://localhost:8000/docs
echo.
echo  Close the two terminal windows to stop the app.
echo ============================================================
echo.
pause
