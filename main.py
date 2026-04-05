"""
StockLens Pro — main.py
=======================
FastAPI entry point. Zero business logic here.

Run locally:
    uvicorn main:app --reload --port 8080
    OR: python main.py

Deploy (Cloud Run):
    gcloud run deploy stocklens --source . --region asia-south1 \
      --memory 512Mi --min-instances 0 --max-instances 3 \
      --set-env-vars GROQ_API_KEY=your_key_here

Environment variables:
    GROQ_API_KEY   required for /ai (get free key at console.groq.com)
"""
import sys
from pathlib import Path

# Add project root to sys.path — makes core/, services/, routers/ importable
# without needing pyproject.toml or pip install -e .
_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from core.config import settings
from core.deps import templates
from routers import ai, calculator, pages, stock
from services.ai import is_available as groq_ok
from services.stock import USE_CURL

app = FastAPI(
    title=settings.APP_TITLE,
    description="Stock analysis · Financial calculators · AI chat",
    version=settings.APP_VERSION,
    docs_url="/api/docs",
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(stock.router)
app.include_router(calculator.router)
app.include_router(ai.router)
app.include_router(pages.router)


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def portfolio(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("portfolio.html", {"request": request})


@app.get("/health", tags=["System"])
async def health() -> dict:
    return {"status": "ok", "version": settings.APP_VERSION,
            "curl_cffi": USE_CURL, "groq": groq_ok()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=True)