"""
core/config.py
All app settings in one place — read from environment variables at startup.
Uses pydantic-settings for type coercion, validation, and .env file support.
"""
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App metadata ──────────────────────────────────────────────────────────
    APP_TITLE: str   = "StockLens Pro"
    APP_VERSION: str = "2.0.0"

    # Controls startup safety checks. Defaults to False so the app works
    # out-of-the-box locally without any environment variables.
    #
    # Behaviour matrix:
    #   PRODUCTION=false + ALLOWED_ORIGINS=*        → WARNING logged, app starts (local dev)
    #   PRODUCTION=false + ALLOWED_ORIGINS=<domain> → normal startup
    #   PRODUCTION=true  + ALLOWED_ORIGINS=*        → RuntimeError, container refuses to start
    #   PRODUCTION=true  + ALLOWED_ORIGINS=<domain> → normal startup  ← what you want in Cloud Run
    #
    # Set both in Cloud Run environment variables:
    #   PRODUCTION=true
    #   ALLOWED_ORIGINS=https://yourdomain.com
    PRODUCTION: bool = False

    # ── Server ────────────────────────────────────────────────────────────────
    PORT: int = Field(default=8080, ge=1, le=65535)

    # ── AI / Groq ─────────────────────────────────────────────────────────────
    MAX_PROMPT_LEN: int  = Field(default=2000, ge=1, le=10000)
    GROQ_API_KEY: str    = ""
    GROQ_MODEL: str      = "llama-3.1-8b-instant"
    GROQ_MAX_TOKENS: int = Field(default=512, ge=1, le=8192)

    # ── CORS ──────────────────────────────────────────────────────────────────
    # Production: ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
    # "*" is only safe for local development.
    ALLOWED_ORIGINS: list[str] = ["*"]

    # ── Rate limiting ─────────────────────────────────────────────────────────
    # Max requests per IP per RATE_LIMIT_PERIOD seconds.
    # Set RATE_LIMIT_CALLS=0 to disable (not recommended in production).
    RATE_LIMIT_CALLS:  int = Field(default=10, ge=0)
    RATE_LIMIT_PERIOD: int = Field(default=60, ge=1)

    # ── Cache TTLs and size caps ───────────────────────────────────────────────
    # Lower QUOTE_CACHE_MAX / HISTORY_CACHE_MAX to reduce memory on free tier.
    QUOTE_CACHE_TTL:   int = Field(default=300,  ge=10)
    HISTORY_CACHE_TTL: int = Field(default=1800, ge=10)
    QUOTE_CACHE_MAX:   int = Field(default=200,  ge=1)
    HISTORY_CACHE_MAX: int = Field(default=100,  ge=1)

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def _parse_origins(cls, v: object) -> list[str]:
        """Accept a comma-separated string from an env var or a plain list."""
        if isinstance(v, str):
            return [o.strip() for o in v.split(",") if o.strip()]
        if isinstance(v, list):
            return [str(item) for item in v]
        raise ValueError(f"ALLOWED_ORIGINS must be a string or list, got {type(v)}")


settings = Settings()
