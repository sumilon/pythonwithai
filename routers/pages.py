"""
routers/pages.py
Simple template-only pages — add new static pages here without touching main.py.
"""
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from core.deps import templates

router = APIRouter()

_PAGES: dict[str, str] = {
    "/swp":    "swp.html",
    "/emi":    "emi.html",
    "/game":   "game.html",
    "/todo":   "todo.html",
    "/vault":  "vault.html",
    "/stroop": "stroop.html",
}

for _path, _tpl in _PAGES.items():
    def _factory(tpl: str):
        async def _view(request: Request) -> HTMLResponse:
            return templates.TemplateResponse(request, tpl)
        name = tpl.replace(".html", "")
        _view.__name__     = name
        _view.__qualname__ = name
        return _view

    router.add_api_route(
        _path, _factory(_tpl),
        methods=["GET"],
        response_class=HTMLResponse,
        tags=["Pages"],
        include_in_schema=False,
    )
