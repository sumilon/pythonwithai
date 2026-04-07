"""
main.py — FastAPI entry point. Zero business logic here.

Run locally:
    uvicorn main:app --reload --port 8080
    OR: python main.py

Deploy (Cloud Run):
    gcloud run deploy stocklens --source . --region asia-south1 \
      --memory 512Mi --min-instances 0 --max-instances 3 \
      --set-env-vars GROQ_API_KEY=your_key_here

Environment variables (see .env.example for full list):
    GROQ_API_KEY      required for /ai  (get free key at console.groq.com)
    ALLOWED_ORIGINS   comma-separated CORS origins — MUST lock down in prod
    GROQ_MODEL        override LLM model (default: llama-3.1-8b-instant)
    GROQ_MAX_TOKENS   override max tokens (default: 512)
    QUOTE_CACHE_TTL   quote cache TTL seconds (default: 300)
    HISTORY_CACHE_TTL history cache TTL seconds (default: 1800)
    QUOTE_CACHE_MAX   max symbols in quote cache (default: 200)
    HISTORY_CACHE_MAX max entries in history cache (default: 100)
"""
import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

# Ensure project root is on sys.path regardless of the launch directory.
# This must run before any local imports.
_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from core.config import settings
from core.deps import templates
from core.ratelimit import RateLimitMiddleware
from routers import ai, calculator, pages, stock
from services.ai import is_available as groq_ok
from services.stock import USE_CURL

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ── Security-headers middleware ───────────────────────────────────────────────

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Attach a minimal set of hardening headers to every HTTP response."""

    # Content-Security-Policy:
    #   default-src 'self'         — block anything not explicitly allowed
    #   script-src  'self' 'unsafe-inline' cdn.jsdelivr.net cdnjs.cloudflare.com
    #                              — allow inline JS (templates) + common CDNs
    #   style-src   'self' 'unsafe-inline' cdn.jsdelivr.net cdnjs.cloudflare.com fonts.googleapis.com
    #   font-src    'self' fonts.gstatic.com data:
    #   img-src     'self' data: https:   — charts, favicons, remote images
    #   connect-src 'self'         — XHR/fetch only to own origin
    #   frame-ancestors 'none'     — equivalent to X-Frame-Options: DENY
    #
    # Tighten script-src by removing 'unsafe-inline' and adding nonces once
    # the templates support it.
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
        response.headers["Content-Security-Policy"]    = self._CSP
        response.headers["X-Content-Type-Options"]     = "nosniff"
        response.headers["X-Frame-Options"]            = "DENY"
        response.headers["X-XSS-Protection"]           = "0"
        response.headers["Referrer-Policy"]            = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"]         = "geolocation=(), microphone=(), camera=()"
        response.headers["Strict-Transport-Security"]  = "max-age=31536000; includeSubDomains"
        return response


# ── Lifespan: startup + graceful shutdown ─────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Cloud Run sends SIGTERM before killing the container.
    FastAPI's lifespan handles graceful shutdown — in-flight requests finish
    before the process exits.
    """
    if settings.ALLOWED_ORIGINS == ["*"]:
        logger.warning(
            "CORS is open to ALL origins (ALLOWED_ORIGINS=*). "
            "Set ALLOWED_ORIGINS to your domain before going to production."
        )
    logger.info(
        "Starting %s v%s | curl_cffi=%s | groq=%s",
        settings.APP_TITLE, settings.APP_VERSION, USE_CURL, groq_ok(),
    )
    yield
    logger.info("Shutting down — draining in-flight requests.")


# ── App factory ───────────────────────────────────────────────────────────────

app = FastAPI(
    title=settings.APP_TITLE,
    description="Stock analysis · Financial calculators · AI chat",
    version=settings.APP_VERSION,
    docs_url="/api/docs",
    redoc_url=None,
    lifespan=lifespan,
)

# Middleware is applied in reverse registration order (last added = outermost).
# Execution order: RateLimit → SecurityHeaders → CORS → router handlers.
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
# Rate limiter is outermost — anonymous abusers are rejected before any
# business logic or auth runs. 5 requests / 60 s per IP by default;
# override via RATE_LIMIT_CALLS / RATE_LIMIT_PERIOD env vars if needed.
app.add_middleware(
    RateLimitMiddleware,
    calls=settings.RATE_LIMIT_CALLS,
    period=settings.RATE_LIMIT_PERIOD,
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
    """Service health check — used by Cloud Run readiness probe."""
    return {
        "status":    "ok",
        "version":   settings.APP_VERSION,
        "curl_cffi": USE_CURL,
        "groq":      groq_ok(),
    }


# ── Global exception handler — never leak tracebacks to the client ────────────

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
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
