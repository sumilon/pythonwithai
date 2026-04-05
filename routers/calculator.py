"""
routers/calculator.py
"""
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from core.deps import templates
from services.calculator import dispatch, indian_format

router = APIRouter()
_BLANK = {"result": None, "calc_type": None, "error": None, "indian_format": indian_format}


@router.get("/calculator", response_class=HTMLResponse, tags=["Calculator"])
async def calculator_get(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("calculator.html", {"request": request, **_BLANK})


@router.post("/calculator", response_class=HTMLResponse, tags=["Calculator"])
async def calculator_post(request: Request) -> HTMLResponse:
    form      = dict(await request.form())
    calc_type = (form.get("type") or "").strip()
    result = error = None
    try:
        result = dispatch(calc_type, form)
    except ValueError as e:
        error = str(e)
    except (KeyError, TypeError):
        error = "Missing or invalid input — please fill all fields."
    except ZeroDivisionError:
        error = "Division by zero — check your inputs."
    except Exception:
        error = "Unexpected error. Please try again."

    return templates.TemplateResponse("calculator.html", {
        "request": request, "result": result,
        "calc_type": calc_type, "error": error, "indian_format": indian_format,
    })