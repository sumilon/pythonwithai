"""
services/ai.py
Groq LLM client — lazy singleton, no FastAPI imports.
"""
import os

from core.config import settings

try:
    from groq import Groq
    _HAS_GROQ = True
except ImportError:
    _HAS_GROQ = False

_client: "Groq | None" = None
_last_key: str = ""


def _get_client() -> "Groq":
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

    Uses model and token limit from centralised settings so there is one
    place to change them — no more duplicated defaults across files.
    """
    res = _get_client().chat.completions.create(
        model=settings.GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=settings.GROQ_MAX_TOKENS,
    )
    return res.choices[0].message.content.strip()


def is_available() -> bool:
    """Return True if groq is installed AND GROQ_API_KEY is set."""
    return _HAS_GROQ and bool(os.environ.get("GROQ_API_KEY", "").strip())
