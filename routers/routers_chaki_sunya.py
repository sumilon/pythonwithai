"""
routers/chaki_sunya.py — Chaki Sunya (Odia tic-tac-toe) page + AI move API.

Follows the same GET-renders / POST-computes shape as routers/calculator.py.
Endpoints are namespaced under /chaki-sunya so they don't collide with the
existing /game (2048) route or any future games.
"""
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, field_validator

from core.deps import templates
from services.chaki_sunya import check_winner, get_ai_move

router = APIRouter()


class BoardCheckRequest(BaseModel):
    board: List[Optional[str]]

    @field_validator("board")
    @classmethod
    def board_must_have_nine_cells(cls, v):
        if len(v) != 9:
            raise ValueError("board must have exactly 9 cells")
        return v


class AIMoveRequest(BaseModel):
    board: List[Optional[str]]
    ai_symbol: str
    difficulty: str = "unbeatable"

    @field_validator("board")
    @classmethod
    def board_must_have_nine_cells(cls, v):
        if len(v) != 9:
            raise ValueError("board must have exactly 9 cells")
        for cell in v:
            if cell not in (None, "X", "O"):
                raise ValueError("each cell must be null, 'X', or 'O'")
        return v

    @field_validator("ai_symbol")
    @classmethod
    def symbol_must_be_x_or_o(cls, v):
        if v not in ("X", "O"):
            raise ValueError("ai_symbol must be 'X' or 'O'")
        return v

    @field_validator("difficulty")
    @classmethod
    def difficulty_must_be_known(cls, v):
        if v not in ("easy", "medium", "unbeatable"):
            raise ValueError("difficulty must be 'easy', 'medium', or 'unbeatable'")
        return v


@router.get("/chaki-sunya", response_class=HTMLResponse, tags=["Chaki Sunya"])
async def chaki_sunya_get(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "chaki_sunya.html")


@router.post("/api/chaki-sunya/check-winner", tags=["Chaki Sunya"])
async def api_check_winner(req: BoardCheckRequest):
    return {"result": check_winner(req.board)}


@router.post("/api/chaki-sunya/ai-move", tags=["Chaki Sunya"])
async def api_ai_move(req: AIMoveRequest):
    if check_winner(req.board) is not None:
        raise HTTPException(status_code=400, detail="Game is already over")
    try:
        move = get_ai_move(req.board, req.ai_symbol, req.difficulty)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"move": move}
