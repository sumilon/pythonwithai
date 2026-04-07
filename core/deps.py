"""
core/deps.py
Shared FastAPI dependencies — single instances reused across all routers.
"""
from pathlib import Path

from fastapi.templating import Jinja2Templates

# Resolve relative to this file so the path is correct regardless of the
# working directory the server is launched from.
_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"

templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))
