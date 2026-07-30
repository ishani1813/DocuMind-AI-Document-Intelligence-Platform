"""DocuMind — AI Document Intelligence Platform. FastAPI entry point."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
import structlog

from app.core.config import settings
from app.core.database import init_db, AsyncSessionLocal
from app.core.vector_store import init_vector_store
from app.llmops import llmops_tracker
from app.api.v1 import auth, documents, chat, search, workspaces, ml, llmops

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting DocuMind API", env=settings.APP_ENV)
    await init_db()
    await init_vector_store()
    llmops_tracker.configure(AsyncSessionLocal)
    logger.info("DocuMind API ready", llm_provider="ollama" if settings.USE_OLLAMA else "openai")
    yield
    logger.info("Shutting down DocuMind API")


app = FastAPI(
    title="DocuMind API",
    description="AI Document Intelligence Platform — RAG, ML insights, and LLMOps observability.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)

app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(documents.router, prefix="/api/v1/documents", tags=["Documents"])
app.include_router(chat.router, prefix="/api/v1/chat", tags=["Chat"])
app.include_router(search.router, prefix="/api/v1/search", tags=["Search"])
app.include_router(workspaces.router, prefix="/api/v1/workspaces", tags=["Workspaces"])
app.include_router(ml.router, prefix="/api/v1/ml", tags=["ML & AI"])
app.include_router(llmops.router, prefix="/api/v1/llmops", tags=["LLMOps"])


@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "version": "1.0.0",
        "service": "DocuMind API",
        "llm_provider": "ollama" if settings.USE_OLLAMA else "openai",
    }
