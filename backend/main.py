"""
AfriHealth Assistant — FastAPI Backend
Entry point: uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

Blueprint (router) pattern:
  Each domain has its own APIRouter registered here with a URL prefix.
  This mirrors Flask's blueprint pattern and keeps routes modular.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.config import settings
from backend.utils.logger import get_logger
from backend.database.db_manager import db_manager
from backend.core.llm_engine import llm_engine
from backend.core.embedding_service import embedding_service
from backend.core.rag_engine import rag_engine

# Routers (blueprints)
from backend.api.routes.system    import system_router
from backend.api.routes.chat      import chat_router
from backend.api.routes.history   import history_router
from backend.api.routes.health    import health_router
from backend.api.routes.documents import documents_router
from backend.api.routes.auth      import auth_router

logger = get_logger(__name__)


# ------------------------------------------------------------------
# Lifespan — startup & shutdown
# ------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Startup ---
    logger.info("Starting %s v%s …", settings.APP_NAME, settings.APP_VERSION)

    # 1. Init database tables
    db_manager.init_tables()
    logger.info("Database ready at %s", settings.DB_PATH)

    # 2. Load LLM (non-blocking warning if model file absent)
    llm_engine.load_model()

    # 3. Load embedding model
    embedding_service.load_model()

    # 4. Init RAG engine (wire dependencies, open ChromaDB)
    rag_engine.set_llm(llm_engine)
    rag_engine.set_embedder(embedding_service)
    rag_engine.initialize()

    logger.info(
        "All systems ready. Knowledge base: %d docs. Model: %s.",
        rag_engine.get_collection_count(),
        "loaded" if llm_engine._model else "stub mode",
    )

    yield  # ← app runs here

    # --- Shutdown ---
    logger.info("Shutting down %s …", settings.APP_NAME)


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

    # CORS — allow Streamlit frontend (localhost:8501) to call this API
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register routers (blueprints) with /api/v1 prefix
    prefix = "/api/v1"
    app.include_router(system_router,    prefix=prefix)
    app.include_router(chat_router,      prefix=prefix)
    app.include_router(history_router,   prefix=prefix)
    app.include_router(health_router,    prefix=prefix)
    app.include_router(documents_router, prefix=prefix)
    app.include_router(auth_router,      prefix=prefix)

    # Root redirect to docs
    @app.get("/", include_in_schema=False)
    async def root():
        return JSONResponse({"message": f"{settings.APP_NAME} API", "docs": "/docs"})

    return app


app = create_app()
