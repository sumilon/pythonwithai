"""
main.py — FastAPI entry point. Zero business logic here.

Run locally:
    uvicorn main:app --reload --port 8080
    OR: python main.py

Deploy (Cloud Run):
    gcloud run deploy stocklens --source . --region asia-south1 \
      --memory 512Mi --min-instances 0 --max-instances 3 \
      --set-env-vars GROQ_API_KEY=your_key_here

    Or build & push the provided Dockerfile:
      docker build -t stocklens . && docker run -p 8080:8080 stocklens

Environment variables (copy .env.example → .env for local dev):
    GROQ_API_KEY      required for /ai  (get free key at console.groq.com)
    PRODUCTION        set true in Cloud Run — open CORS becomes a hard startup error
    ALLOWED_ORIGINS   comma-separated CORS origins — MUST lock down in prod
    GROQ_MODEL        override LLM model (default: llama-3.1-8b-instant)
    GROQ_MAX_TOKENS   override max tokens (default: 512)
    QUOTE_CACHE_TTL   quote cache TTL seconds (default: 300)
    HISTORY_CACHE_TTL history cache TTL seconds (default: 1800)
    QUOTE_CACHE_MAX   max symbols in quote cache (default: 200)
    HISTORY_CACHE_MAX max entries in history cache (default: 100)

Middleware execution order (outermost → innermost):
    RateLimitMiddleware → SecurityHeadersMiddleware → GZipMiddleware → CORSMiddleware
"""
import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

# Ensure project root is on sys.path regardless of the launch directory.
_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.gzip import GZipMiddleware

from core.config import settings
from core.deps import templates
from core.ratelimit import RateLimitMiddleware
from routers import ai, calculator, pages, stock
from services.ai import is_available as groq_ok
from services.stock import USE_CURL, _SESSION as curl_session

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Attach security hardening headers to every HTTP response.

    CSP allows inline scripts/styles (required by current templates) and
    whitelists jsDelivr, cdnjs, and Google Fonts. Tighten script-src by
    removing 'unsafe-inline' and adding per-request nonces once the
    templates are updated to support them.
    """

    _CSP = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' cdn.jsdelivr.net cdnjs.cloudflare.com; "
        "style-src 'self' 'unsafe-inline' cdn.jsdelivr.net cdnjs.cloudflare.com fonts.googleapis.com; "
        "font-src 'self' fonts.gstatic.com data:; "
        "img-src 'self' data: https:; "
        "connect-src 'self'; "
        "frame-ancestors 'none';"
    )

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["Content-Security-Policy"]   = self._CSP
        response.headers["X-Content-Type-Options"]    = "nosniff"
        response.headers["X-Frame-Options"]           = "DENY"
        response.headers["X-XSS-Protection"]          = "0"
        response.headers["Referrer-Policy"]           = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"]        = "geolocation=(), microphone=(), camera=()"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup checks and graceful shutdown.

    Cloud Run sends SIGTERM before terminating the container; FastAPI's
    lifespan ensures in-flight requests drain before the process exits.
    """
    if settings.ALLOWED_ORIGINS == ["*"]:
        msg = (
            "CORS is open to ALL origins (ALLOWED_ORIGINS=*). "
            "Set ALLOWED_ORIGINS to your domain in the Cloud Run environment variables."
        )
        if settings.PRODUCTION:
            # Hard failure — refuse to start with an open CORS policy in prod.
            raise RuntimeError(msg)
        logger.warning(msg)

    logger.info(
        "Starting %s v%s | production=%s | curl_cffi=%s | groq=%s",
        settings.APP_TITLE, settings.APP_VERSION,
        settings.PRODUCTION, USE_CURL, groq_ok(),
    )
    yield
    logger.info("Shutting down — draining in-flight requests.")
    if curl_session is not None:
        try:
            curl_session.close()
            logger.info("curl_cffi session closed.")
        except Exception:
            pass


app = FastAPI(
    title=settings.APP_TITLE,
    description="Stock analysis · Financial calculators · AI chat",
    version=settings.APP_VERSION,
    docs_url="/api/docs",
    redoc_url=None,
    lifespan=lifespan,
)

# Middleware is registered in reverse execution order — the last one added
# runs first. RateLimitMiddleware is added last so it is outermost, rejecting
# abusive IPs before any business logic or auth runs.
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Accept"],
)
app.add_middleware(
    RateLimitMiddleware,
    calls=settings.RATE_LIMIT_CALLS,
    period=settings.RATE_LIMIT_PERIOD,
)

app.include_router(stock.router)
app.include_router(calculator.router)
app.include_router(ai.router)
app.include_router(pages.router)


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def portfolio(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "portfolio.html")


@app.get("/health", tags=["System"])
async def health() -> dict:
    """Service health check — used by Cloud Run readiness probe."""
    return {
        "status":    "ok",
        "version":   settings.APP_VERSION,
        "curl_cffi": USE_CURL,
        "groq":      groq_ok(),
    }


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all handler — logs the full traceback server-side, returns a
    generic message to the client so internal details are never leaked."""
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=True,
        log_level="info",
    )
