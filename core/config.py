"""
core/config.py
All app settings in one place — read from environment variables at startup.
Uses python-dotenv for .env file support and plain os.environ for reading values.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env file if it exists (no-op when the file is absent, e.g. in Cloud Run).
load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=False)


def _int(name: str, default: int, ge: int | None = None, le: int | None = None) -> int:
    raw = os.environ.get(name, "").strip()
    val = int(raw) if raw else default
    if ge is not None and val < ge:
        raise ValueError(f"{name}={val} must be >= {ge}")
    if le is not None and val > le:
        raise ValueError(f"{name}={val} must be <= {le}")
    return val


def _bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name, "").strip().lower()
    if not raw:
        return default
    return raw in ("1", "true", "yes", "on")


def _str(name: str, default: str) -> str:
    return os.environ.get(name, "").strip() or default


def _origins(name: str) -> list[str]:
    """Parse ALLOWED_ORIGINS from a comma-separated env var string."""
    raw = os.environ.get(name, "").strip()
    if not raw:
        return ["*"]
    return [o.strip() for o in raw.split(",") if o.strip()]


class _Settings:
    """
    Immutable-style settings container populated once at import time.

    Behaviour matrix (PRODUCTION × ALLOWED_ORIGINS):
      PRODUCTION=false + ALLOWED_ORIGINS=*        → WARNING logged, app starts (local dev)
      PRODUCTION=false + ALLOWED_ORIGINS=<domain> → normal startup
      PRODUCTION=true  + ALLOWED_ORIGINS=*        → RuntimeError, container refuses to start
      PRODUCTION=true  + ALLOWED_ORIGINS=<domain> → normal startup  ← Cloud Run target

    Set both in Cloud Run environment variables:
      PRODUCTION=true
      ALLOWED_ORIGINS=https://yourdomain.com
    """

    # ── App metadata ──────────────────────────────────────────────────────────
    APP_TITLE:   str = "StockLens Pro"
    APP_VERSION: str = "2.0.0"

    # ── Runtime flags ─────────────────────────────────────────────────────────
    PRODUCTION: bool = _bool("PRODUCTION", False)

    # ── Server ────────────────────────────────────────────────────────────────
    PORT: int = _int("PORT", 8080, ge=1, le=65535)

    # ── AI / Groq ─────────────────────────────────────────────────────────────
    MAX_PROMPT_LEN: int  = _int("MAX_PROMPT_LEN",  2000, ge=1,  le=10000)
    GROQ_API_KEY:   str  = _str("GROQ_API_KEY",    "")
    GROQ_MODEL:     str  = _str("GROQ_MODEL",      "llama-3.1-8b-instant")
    GROQ_MAX_TOKENS: int = _int("GROQ_MAX_TOKENS", 512,  ge=1,  le=8192)

    # ── CORS ──────────────────────────────────────────────────────────────────
    # Production: ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
    # Default "*" is only safe for local development.
    ALLOWED_ORIGINS: list[str] = _origins("ALLOWED_ORIGINS")

    # ── Rate limiting ─────────────────────────────────────────────────────────
    # Max requests per IP per RATE_LIMIT_PERIOD seconds.
    # Set RATE_LIMIT_CALLS=0 to disable (not recommended in production).
    RATE_LIMIT_CALLS:  int = _int("RATE_LIMIT_CALLS",  10, ge=0)
    RATE_LIMIT_PERIOD: int = _int("RATE_LIMIT_PERIOD", 60, ge=1)

    # ── Cache TTLs and size caps ───────────────────────────────────────────────
    # Lower QUOTE_CACHE_MAX / HISTORY_CACHE_MAX to reduce memory on free tier.
    QUOTE_CACHE_TTL:   int = _int("QUOTE_CACHE_TTL",   300,  ge=10)
    HISTORY_CACHE_TTL: int = _int("HISTORY_CACHE_TTL", 1800, ge=10)
    QUOTE_CACHE_MAX:   int = _int("QUOTE_CACHE_MAX",   200,  ge=1)
    HISTORY_CACHE_MAX: int = _int("HISTORY_CACHE_MAX", 100,  ge=1)


settings = _Settings()
