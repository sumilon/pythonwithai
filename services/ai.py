"""
services/ai.py
Groq LLM client — lazy singleton, no FastAPI imports.
"""
from __future__ import annotations

import logging
import os

from core.config import settings

logger = logging.getLogger(__name__)

# Groq is optional — initialise to None so the symbol always exists,
# then attempt the real import. is_available() returns False when absent.
Groq = None  # type: ignore[assignment,misc]
_HAS_GROQ = False
try:
    from groq import Groq  # type: ignore[assignment]
    _HAS_GROQ = True
except ImportError:
    pass

_client: Groq | None = None  # type: ignore[valid-type]
_last_key: str = ""

# Known user-friendly error substrings (matched case-insensitively).
# These are safe to forward to the user; anything else is hidden.
_USER_ERRORS: tuple[str, ...] = (
    "invalid api key",
    "rate limit",
    "context_length_exceeded",
    "model not found",
    "insufficient_quota",
)


def _get_client() -> Groq:  # type: ignore[return]
    global _client, _last_key

    if not _HAS_GROQ:
        raise RuntimeError("groq package not installed. Run: pip install groq")

    key = os.environ.get("GROQ_API_KEY", "").strip()
    if not key:
        raise RuntimeError(
            "GROQ_API_KEY environment variable is not set. "
            "Get a free key at console.groq.com"
        )

    # Recreate client only if key changed (handles hot env-var updates)
    if _client is None or key != _last_key:
        _client   = Groq(api_key=key)
        _last_key = key

    return _client


def chat(prompt: str) -> str:
    """Send prompt to Groq and return the text response.

    Raises RuntimeError with a safe, user-friendly message on failure.
    Internal details are logged but never returned to callers.
    """
    try:
        res = _get_client().chat.completions.create(
            model=settings.GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=settings.GROQ_MAX_TOKENS,
            timeout=30,  # fail fast — do not hang the event loop thread
        )
        return res.choices[0].message.content.strip()
    except RuntimeError:
        # Configuration errors — safe to re-raise as-is
        raise
    except Exception as exc:
        msg = str(exc).lower()
        for known in _USER_ERRORS:
            if known in msg:
                # Re-raise with cleaner, safe message
                raise RuntimeError(str(exc)) from exc
        # Unknown / internal error — log details but hide from caller
        logger.exception("Groq API error (hidden from user)")
        raise RuntimeError("The AI service returned an error. Please try again shortly.") from exc


def is_available() -> bool:
    """Return True if groq is installed AND GROQ_API_KEY is set."""
    return _HAS_GROQ and bool(os.environ.get("GROQ_API_KEY", "").strip())
