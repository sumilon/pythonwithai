"""
routers/ai.py — AI chat via Groq LLM
"""
import asyncio
import logging

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from core.config import settings
from core.deps import templates
from services import ai as ai_svc

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/ai", response_class=HTMLResponse, tags=["AI"])
async def ai_get(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("ai.html", {
        "request": request,
        "answer":  "",
        "error":   "",
        "prompt":  "",
    })


@router.post("/ai", response_class=HTMLResponse, tags=["AI"])
async def ai_post(request: Request) -> HTMLResponse:
    form   = await request.form()
    prompt = (form.get("prompt") or "").strip()
    answer = ""
    error  = ""

    if not prompt:
        error = "Please enter a message."
    elif len(prompt) > settings.MAX_PROMPT_LEN:
        error = f"Message too long (max {settings.MAX_PROMPT_LEN} characters)."
    elif not ai_svc.is_available():
        error = (
            "AI service is not configured. "
            "Set the GROQ_API_KEY environment variable and restart the server. "
            "Get a free key at console.groq.com"
        )
    else:
        try:
            answer = await asyncio.to_thread(ai_svc.chat, prompt)
        except RuntimeError as exc:
            # RuntimeError from ai_svc.chat contains a safe, user-facing message
            error = str(exc)
        except Exception:
            logger.exception("Unexpected error in AI router")
            error = "An unexpected error occurred. Please try again."

    return templates.TemplateResponse("ai.html", {
        "request": request,
        "answer":  answer,
        "error":   error,
        "prompt":  prompt,
    })
