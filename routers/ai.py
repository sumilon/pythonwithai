"""
routers/ai.py — AI chat via Groq LLM
"""
import asyncio
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from core.deps import templates
from services import ai as ai_svc

router = APIRouter()

_MAX_LEN = 2000


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
    elif len(prompt) > _MAX_LEN:
        error = f"Message too long (max {_MAX_LEN} characters)."
    elif not ai_svc.is_available():
        error = (
            "AI service is not configured. "
            "Set the GROQ_API_KEY environment variable and restart the server. "
            "Get a free key at console.groq.com"
        )
    else:
        try:
            loop   = asyncio.get_event_loop()
            answer = await loop.run_in_executor(None, ai_svc.chat, prompt)
        except Exception as exc:
            error = str(exc)

    return templates.TemplateResponse("ai.html", {
        "request": request,
        "answer":  answer,
        "error":   error,
        "prompt":  prompt,   # passed explicitly — template must NOT use request.form
    })
