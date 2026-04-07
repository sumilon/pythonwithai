"""
core/deps.py
Shared FastAPI dependencies — single instances reused across all routers.
"""
from pathlib import Path

from fastapi.templating import Jinja2Templates

# Resolve templates path relative to this file so it works regardless of
# the working directory the process is launched from.
_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"

# One Jinja2Templates instance shared by all routers (saves ~15 MB RAM)
templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))
