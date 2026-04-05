"""
services/ai.py
Groq LLM client — lazy singleton, no FastAPI imports.

Fix: GROQ_API_KEY is read fresh each call via os.environ.get()
instead of being cached at import time, so env vars set after
process start are always picked up.
"""
import os

try:
    from groq import Groq
    _HAS_GROQ = True
except ImportError:
    _HAS_GROQ = False

_client = None
_last_key: str = ""


def _get_client() -> "Groq":
    global _client, _last_key

    if not _HAS_GROQ:
        raise RuntimeError(
            "groq package not installed. Run: pip install groq"
        )

    # Read key fresh every call — handles env vars set after startup
    key = os.environ.get("GROQ_API_KEY", "").strip()
    if not key:
        raise RuntimeError(
            "GROQ_API_KEY environment variable is not set. "
            "Get a free key at console.groq.com then set it with: "
            "set GROQ_API_KEY=your_key_here   (Windows CMD) "
            "$env:GROQ_API_KEY='your_key'     (PowerShell)"
        )

    # Recreate client if key changed
    if _client is None or key != _last_key:
        _client   = Groq(api_key=key)
        _last_key = key

    return _client


def chat(prompt: str, model: str = "llama-3.1-8b-instant", max_tokens: int = 1024) -> str:
    """Send prompt to Groq and return the text response."""
    res = _get_client().chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens,
    )
    return res.choices[0].message.content.strip()


def is_available() -> bool:
    """Return True if groq is installed AND GROQ_API_KEY is set."""
    return _HAS_GROQ and bool(os.environ.get("GROQ_API_KEY", "").strip())
