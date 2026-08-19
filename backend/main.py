"""
AfriHealth Assistant - FastAPI Backend
Local entry point: uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
Container entry point may bind to 0.0.0.0, which is not a browser URL.

Blueprint (router) pattern:
  Each domain has its own APIRouter registered here with a URL prefix.
  This mirrors Flask's blueprint pattern and keeps routes modular.
"""

from contextlib import asynccontextmanager

from pathlib import Path
import os
from dotenv import load_dotenv

# Load environment variables from project .env into os.environ so
# modules using os.getenv(...) (e.g. GOOGLE_API_KEY) can read them.
dotenv_path = Path(__file__).resolve().parent.parent / ".env"
if dotenv_path.exists():
    load_dotenv(dotenv_path)

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
import time

from backend.config import settings
from backend.utils.logger import get_logger
from backend.database.db_manager import db_manager
from backend.core.llm_engine import llm_engine
from backend.core.embedding_service import embedding_service
from backend.core.rag_engine import rag_engine

# Routers (blueprints)
from backend.api.routes.system    import system_router
from backend.api.routes.auth      import auth_router
from backend.api.routes.chat      import chat_router
from backend.api.routes.history   import history_router, conversation_router
from backend.api.routes.health    import health_router
from backend.api.routes.documents import documents_router
from backend.api.routes.patients  import patients_router, visits_router
from backend.api.routes.settings  import settings_router
from backend.api.routes.online    import online_router
from backend.api.routes.clinical  import router as clinical_router
from backend.api.routes.voice import voice_router
from backend.api.routes.outbreaks import outbreaks_router
from backend.api.routes.symptom_checker import symptom_checker_router
from backend.api.routes.medications import medications_router
from backend.api.routes.admin import admin_router

logger = get_logger(__name__)


# ------------------------------------------------------------------
# Lifespan - startup & shutdown
# ------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Startup ---
    logger.info("Starting %s v%s ...", settings.APP_NAME, settings.APP_VERSION)

    # 1. Init database tables
    db_manager.init_tables()
    logger.info("Database ready at %s", settings.DB_PATH)

    # 2. Wire AI dependencies without blocking API availability. The LLM,
    # embedding model, and Chroma vector store all lazy-load on first use.
    rag_engine.set_llm(llm_engine)
    rag_engine.set_embedder(embedding_service)

    logger.info("API ready. AI services will lazy-load on first clinical request.")

    yield  # <- app runs here

    # --- Shutdown ---
    logger.info("Shutting down %s ...", settings.APP_NAME)


# ------------------------------------------------------------------
# App factory
# ------------------------------------------------------------------
def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description=(
            "100% offline AI medical assistant backend for African communities. "
            "Powers the AfriHealth Assistant Streamlit frontend via REST + streaming."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    class ApiV1PrefixMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request: Request, call_next):
            if request.url.path.startswith("/api/v1"):
                new_path = request.url.path[len("/api/v1"):] or "/"
                request.scope["path"] = new_path
                request.scope["raw_path"] = new_path.encode("utf-8")
            return await call_next(request)

    app.add_middleware(ApiV1PrefixMiddleware)

    @app.middleware("http")
    async def request_logging(request: Request, call_next):
        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            logger.exception("Unhandled request error: %s %s", request.method, request.url.path)
            raise
        elapsed = (time.perf_counter() - started) * 1000
        logger.info("%s %s -> %s (%.2f ms)", request.method, request.url.path, response.status_code, elapsed)
        response.headers["X-Process-Time-Ms"] = f"{elapsed:.2f}"
        return response

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        return JSONResponse(status_code=422, content={"error": "validation_error", "detail": exc.errors()})

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        return JSONResponse(status_code=exc.status_code, content={"error": "request_error", "detail": exc.detail})

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        logger.exception("Unhandled application exception")
        return JSONResponse(status_code=500, content={"error": "internal_server_error", "detail": "An unexpected server error occurred."})

    # CORS - allow Streamlit frontend (localhost:8501) to call this API
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_origin_regex=settings.ALLOWED_ORIGIN_REGEX or None,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register routers at the root to match the frontend API client and current docs.
    prefix = ""
    app.include_router(system_router,    prefix=prefix)
    app.include_router(auth_router,      prefix=prefix)
    app.include_router(chat_router,      prefix=prefix)
    app.include_router(history_router,   prefix=prefix)
    app.include_router(conversation_router, prefix=prefix)
    app.include_router(documents_router, prefix=prefix)
    app.include_router(patients_router,  prefix=prefix)
    app.include_router(visits_router,    prefix=prefix)
    app.include_router(health_router,    prefix=prefix)
    app.include_router(settings_router,  prefix=prefix)
    app.include_router(online_router,    prefix=prefix)
    app.include_router(clinical_router,  prefix=prefix)
    app.include_router(voice_router,           prefix=prefix)
    app.include_router(outbreaks_router,       prefix=prefix)
    app.include_router(symptom_checker_router, prefix=prefix)
    app.include_router(medications_router,     prefix=prefix)
    app.include_router(admin_router,           prefix=prefix)

    # Root redirect to docs
    @app.get("/", include_in_schema=False)
    async def root():
        return JSONResponse({"message": f"{settings.APP_NAME} API", "docs": "/docs"})

    return app


app = create_app()
