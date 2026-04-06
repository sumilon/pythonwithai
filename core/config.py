"""
core/config.py
All app settings in one place — read from environment variables at startup.
Uses pydantic-settings for type coercion, validation, and optional .env support.

Install: pip install pydantic-settings
"""
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # ignore unknown env vars — do NOT crash
    )

    # ── App metadata ──────────────────────────────────────────────────────────
    APP_TITLE: str    = "StockLens Pro"
    APP_VERSION: str  = "2.0.0"

    # ── Server ────────────────────────────────────────────────────────────────
    PORT: int = Field(default=8080, ge=1, le=65535)

    # ── AI / Groq ─────────────────────────────────────────────────────────────
    MAX_PROMPT_LEN: int  = Field(default=2000, ge=1, le=10000)
    GROQ_API_KEY: str    = ""
    GROQ_MODEL: str      = "llama-3.1-8b-instant"
    GROQ_MAX_TOKENS: int = Field(default=512, ge=1, le=8192)

    # ── CORS ──────────────────────────────────────────────────────────────────
    # Production example: ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
    # Wildcard "*" is only safe for local development.
    ALLOWED_ORIGINS: list[str] = ["*"]

    # ── Cache TTLs (seconds) ──────────────────────────────────────────────────
    QUOTE_CACHE_TTL: int   = Field(default=300,  ge=10)
    HISTORY_CACHE_TTL: int = Field(default=1800, ge=10)

    # ── Cache max entries (prevents unbounded memory growth) ──────────────────
    QUOTE_CACHE_MAX: int   = Field(default=200, ge=1)
    HISTORY_CACHE_MAX: int = Field(default=100, ge=1)

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def _parse_origins(cls, v: object) -> list[str]:
        """Accept comma-separated string from env var or a list directly."""
        if isinstance(v, str):
            return [o.strip() for o in v.split(",") if o.strip()]
        if isinstance(v, list):
            return [str(item) for item in v]
        raise ValueError(f"ALLOWED_ORIGINS must be a string or list, got {type(v)}")


settings = Settings()
