"""
main.py — FastAPI entry point. Zero business logic here.

Run locally:
    uvicorn main:app --reload --port 8080
    OR: python main.py

Deploy (Cloud Run):
    gcloud run deploy stocklens --source . --region asia-south1 \
      --memory 512Mi --min-instances 0 --max-instances 3 \
      --set-env-vars GROQ_API_KEY=your_key_here

Environment variables:
    GROQ_API_KEY      required for /ai  (get free key at console.groq.com)
    ALLOWED_ORIGINS   comma-separated CORS origins (default "*" — lock down in prod)
    GROQ_MODEL        override LLM model (default: llama-3.1-8b-instant)
    GROQ_MAX_TOKENS   override max tokens (default: 512)
    QUOTE_CACHE_TTL   quote cache TTL seconds (default: 300)
    HISTORY_CACHE_TTL history cache TTL seconds (default: 1800)
    QUOTE_CACHE_MAX   max symbols in quote cache (default: 200)
    HISTORY_CACHE_MAX max entries in history cache (default: 100)
"""
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

# Ensure project root is importable regardless of launch directory
_ROOT = Path(__file__).resolve().parent
import sys
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse

from core.config import settings
from core.deps import templates
from routers import ai, calculator, pages, stock
from services.ai import is_available as groq_ok
from services.stock import USE_CURL

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ── Lifespan: startup + graceful shutdown ─────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Cloud Run sends SIGTERM before killing the container.
    FastAPI's lifespan context handles graceful shutdown automatically —
    in-flight requests finish before the process exits.
    """
    logger.info(
        "Starting %s v%s | curl_cffi=%s | groq=%s",
        settings.APP_TITLE, settings.APP_VERSION, USE_CURL, groq_ok()
    )
    yield
    logger.info("Shutting down — draining in-flight requests.")


# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title=settings.APP_TITLE,
    description="Stock analysis · Financial calculators · AI chat",
    version=settings.APP_VERSION,
    docs_url="/api/docs",
    redoc_url=None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,   # locked down via env var in prod
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(stock.router)
app.include_router(calculator.router)
app.include_router(ai.router)
app.include_router(pages.router)


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def portfolio(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("portfolio.html", {"request": request})


@app.get("/health", tags=["System"])
async def health() -> dict:
    return {
        "status":     "ok",
        "version":    settings.APP_VERSION,
        "curl_cffi":  USE_CURL,
        "groq":       groq_ok(),
    }


# ── Global exception handler — never leak tracebacks to the client ────────────

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


# ── Local dev entrypoint ──────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=True,
        log_level="info",
    )
