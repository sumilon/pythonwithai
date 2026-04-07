"""
routers/ai.py — AI chat via Groq LLM
"""
import asyncio
import logging

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse

from core.config import settings
from core.deps import templates
from services import ai as ai_svc

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/ai", response_class=HTMLResponse, tags=["AI"])
async def ai_get(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("ai.html", {"request": request})


@router.post("/api/chat", tags=["AI"])
async def api_chat(request: Request) -> JSONResponse:
    """
    JSON endpoint consumed by the typewriter UI.
    Returns: {"answer": "..."} or {"error": "..."}
    """
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON in request body."}, status_code=400)
    prompt = (body.get("prompt") or "").strip()

    if not prompt:
        return JSONResponse({"error": "Please enter a message."}, status_code=400)

    if len(prompt) > settings.MAX_PROMPT_LEN:
        return JSONResponse(
            {"error": f"Message too long (max {settings.MAX_PROMPT_LEN} characters)."},
            status_code=400,
        )

    if not ai_svc.is_available():
        return JSONResponse(
            {"error": (
                "AI service is not configured. "
                "Set the GROQ_API_KEY environment variable and restart the server."
            )},
            status_code=503,
        )

    try:
        answer = await asyncio.to_thread(ai_svc.chat, prompt)
        return JSONResponse({"answer": answer})
    except RuntimeError as exc:
        return JSONResponse({"error": str(exc)}, status_code=502)
    except Exception:
        logger.exception("Unexpected error in /api/chat")
        return JSONResponse({"error": "An unexpected error occurred. Please try again."}, status_code=500)
