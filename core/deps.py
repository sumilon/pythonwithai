"""
core/deps.py
Shared FastAPI dependencies — single instances reused across all routers.
"""
from fastapi.templating import Jinja2Templates

# One Jinja2Templates instance shared by all routers (saves ~15 MB RAM)
templates = Jinja2Templates(directory="templates")