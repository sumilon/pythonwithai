"""
core/config.py
All app settings in one place — read from environment variables at startup.
"""
import os


class Settings:
    APP_TITLE: str       = "StockLens Pro"
    APP_VERSION: str     = "2.0.0"
    MAX_PROMPT_LEN: int  = 2000
    GROQ_API_KEY: str    = os.environ.get("GROQ_API_KEY", "")
    GROQ_MODEL: str      = "llama-3.1-8b-instant"
    GROQ_MAX_TOKENS: int = 512


settings = Settings()