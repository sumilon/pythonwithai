"""
routers/calculator.py — financial calculator page (GET renders form, POST computes result).
"""
import logging

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from core.deps import templates
from services.calculator import dispatch, indian_format

logger = logging.getLogger(__name__)
router = APIRouter()


def _ctx(**kwargs) -> dict:
    """Build a template context dict with safe defaults."""
    return {
        "result":        None,
        "calc_type":     None,
        "error":         None,
        "indian_format": indian_format,
        **kwargs,
    }


@router.get("/calculator", response_class=HTMLResponse, tags=["Calculator"])
async def calculator_get(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("calculator.html", {"request": request, **_ctx()})


@router.post("/calculator", response_class=HTMLResponse, tags=["Calculator"])
async def calculator_post(request: Request) -> HTMLResponse:
    form      = dict(await request.form())
    calc_type = (form.get("type") or "").strip()
    result = error = None

    try:
        result = dispatch(calc_type, form)
    except ValueError as exc:
        error = str(exc)
    except (KeyError, TypeError):
        error = "Missing or invalid input — please fill all fields."
    except ZeroDivisionError:
        error = "Division by zero — check your inputs."
    except Exception:
        logger.exception("Unexpected calculator error: calc_type=%r form=%r", calc_type, form)
        error = "Unexpected error. Please try again."

    return templates.TemplateResponse("calculator.html", {
        "request": request,
        **_ctx(result=result, calc_type=calc_type, error=error),
    })
