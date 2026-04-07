"""
services/ai.py
Groq LLM client — lazy singleton, no FastAPI imports.
"""
from __future__ import annotations

import logging
import os
import threading

from core.config import settings

logger = logging.getLogger(__name__)

# Groq is an optional dependency. Initialise to None so the name always
# exists at module level; is_available() returns False when it is absent.
Groq = None  # type: ignore[assignment,misc]
_HAS_GROQ = False
try:
    from groq import Groq  # type: ignore[assignment]
    _HAS_GROQ = True
except ImportError:
    pass

_client: Groq | None = None  # type: ignore[valid-type]
_last_key: str = ""
_client_lock = threading.Lock()

# Error substrings that are safe to surface to the user as-is.
# Anything not in this list is replaced with a generic message.
_USER_ERRORS: tuple[str, ...] = (
    "invalid api key",
    "rate limit",
    "context_length_exceeded",
    "model not found",
    "insufficient_quota",
)

# Translation table that strips null bytes and non-printable control
# characters (except tab, newline, carriage-return) from user prompts.
_CTRL_CHARS = "".join(chr(c) for c in range(32) if c not in (9, 10, 13))
_CTRL_TABLE = str.maketrans("", "", _CTRL_CHARS)


def _sanitize_prompt(prompt: str) -> str:
    """Strip control characters that can cause cryptic upstream API errors."""
    return prompt.translate(_CTRL_TABLE).strip()


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

    # Re-create the client only when the key changes (e.g. hot-swap in dev).
    with _client_lock:
        if _client is None or key != _last_key:
            _client   = Groq(api_key=key)
            _last_key = key
        return _client


def chat(prompt: str) -> str:
    """Send a prompt to Groq and return the text response.

    Sanitises the prompt first. Raises RuntimeError with a user-safe
    message on failure — internal details are logged, never returned.
    """
    clean_prompt = _sanitize_prompt(prompt)
    try:
        res = _get_client().chat.completions.create(
            model=settings.GROQ_MODEL,
            messages=[{"role": "user", "content": clean_prompt}],
            max_tokens=settings.GROQ_MAX_TOKENS,
            timeout=30,
        )
        return res.choices[0].message.content.strip()
    except RuntimeError:
        raise
    except Exception as exc:
        msg = str(exc).lower()
        for known in _USER_ERRORS:
            if known in msg:
                raise RuntimeError(str(exc)) from exc
        logger.exception("Groq API error (hidden from user)")
        raise RuntimeError("The AI service returned an error. Please try again shortly.") from exc


def is_available() -> bool:
    """Return True if groq is installed and GROQ_API_KEY is set."""
    return _HAS_GROQ and bool(os.environ.get("GROQ_API_KEY", "").strip())
