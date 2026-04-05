"""
core/config.py
All app settings in one place — read from environment variables at startup.
"""
import os


class Settings:
    APP_TITLE: str        = "StockLens Pro"
    APP_VERSION: str      = "2.0.0"

    # Server
    PORT: int             = int(os.environ.get("PORT", "8080"))

    # AI
    MAX_PROMPT_LEN: int   = 2000
    GROQ_API_KEY: str     = os.environ.get("GROQ_API_KEY", "")
    GROQ_MODEL: str       = os.environ.get("GROQ_MODEL", "llama-3.1-8b-instant")
    GROQ_MAX_TOKENS: int  = int(os.environ.get("GROQ_MAX_TOKENS", "512"))

    # CORS — comma-separated list of allowed origins, or "*" for dev
    # Production example: ALLOWED_ORIGINS=https://yourdomain.com
    ALLOWED_ORIGINS: list[str] = [
        o.strip()
        for o in os.environ.get("ALLOWED_ORIGINS", "*").split(",")
        if o.strip()
    ]

    # Cache TTLs (seconds)
    QUOTE_CACHE_TTL: int   = int(os.environ.get("QUOTE_CACHE_TTL", "300"))
    HISTORY_CACHE_TTL: int = int(os.environ.get("HISTORY_CACHE_TTL", "1800"))

    # Max unique symbols per cache — prevents unbounded memory growth
    QUOTE_CACHE_MAX: int   = int(os.environ.get("QUOTE_CACHE_MAX", "200"))
    HISTORY_CACHE_MAX: int = int(os.environ.get("HISTORY_CACHE_MAX", "100"))


settings = Settings()
