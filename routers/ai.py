"""
routers/ai.py — AI chat via Groq LLM
"""
import asyncio
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from core.config import settings
from core.deps import templates
from services import ai as ai_svc

router = APIRouter()


@router.get("/ai", response_class=HTMLResponse, tags=["AI"])
async def ai_get(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("ai.html", {
        "request": request,
        "answer": "",
        "error": "",
        "prompt": "",
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
            "Set the GROQ_API_KEY environment variable. "
            "Get a free key at console.groq.com"
        )
    else:
        try:
            # Run blocking Groq call in thread executor
            loop   = asyncio.get_event_loop()
            answer = await loop.run_in_executor(None, ai_svc.chat, prompt)
        except Exception as e:
            error = f"AI error: {str(e)}"

    return templates.TemplateResponse("ai.html", {
        "request": request,
        "answer":  answer,
        "error":   error,
        "prompt":  prompt,
    })