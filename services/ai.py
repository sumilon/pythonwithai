"""
services/ai.py
Groq LLM client — lazy singleton, no FastAPI imports.
"""
from core.config import settings

try:
    from groq import Groq
    _HAS_GROQ = True
except ImportError:
    _HAS_GROQ = False

_client = None


def _get_client():
    global _client
    if not _HAS_GROQ:
        raise RuntimeError("groq package not installed. Run: pip install groq")
    if not settings.GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY environment variable is not set.")
    if _client is None:
        _client = Groq(api_key=settings.GROQ_API_KEY)
    return _client


def chat(prompt: str) -> str:
    res = _get_client().chat.completions.create(
        model=settings.GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=settings.GROQ_MAX_TOKENS,
    )
    return res.choices[0].message.content.strip()


def is_available() -> bool:
    return _HAS_GROQ and bool(settings.GROQ_API_KEY)