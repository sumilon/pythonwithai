"""
services/chaki_sunya.py
Core game logic for Chaki Sunya (ଛକି ଶୁନ — the classic Odia notebook grid
game, known elsewhere as tic-tac-toe).

Pure logic, no framework dependencies — mirrors the project's convention
(see services/calculator.py). Stateless: the client owns the board, the
server just (a) checks a board for a winner and (b) picks the AI's move.
"""
from __future__ import annotations

import random
from typing import List, Optional

Board = List[Optional[str]]

WIN_LINES = [
    (0, 1, 2), (3, 4, 5), (6, 7, 8),  # rows
    (0, 3, 6), (1, 4, 7), (2, 5, 8),  # columns
    (0, 4, 8), (2, 4, 6),             # diagonals
]


def check_winner(board: Board) -> Optional[dict]:
    """Return {'winner': 'X'|'O', 'line': (a,b,c)} or {'winner': 'draw'} or None."""
    for line in WIN_LINES:
        a, b, c = line
        if board[a] is not None and board[a] == board[b] == board[c]:
            return {"winner": board[a], "line": line}
    if all(cell is not None for cell in board):
        return {"winner": "draw", "line": None}
    return None


def _other(symbol: str) -> str:
    return "O" if symbol == "X" else "X"


def _minimax(board: Board, symbol: str, ai_symbol: str, depth: int, alpha: int, beta: int) -> int:
    result = check_winner(board)
    if result is not None:
        if result["winner"] == "draw":
            return 0
        return (10 - depth) if result["winner"] == ai_symbol else (depth - 10)

    is_maximizing = symbol == ai_symbol
    best = -1000 if is_maximizing else 1000

    for i in range(9):
        if board[i] is None:
            board[i] = symbol
            score = _minimax(board, _other(symbol), ai_symbol, depth + 1, alpha, beta)
            board[i] = None

            if is_maximizing:
                best = max(best, score)
                alpha = max(alpha, best)
            else:
                best = min(best, score)
                beta = min(beta, best)

            if beta <= alpha:
                break
    return best


def _best_move(board: Board, ai_symbol: str) -> int:
    best_score = -1000
    best_move = next(i for i in range(9) if board[i] is None)
    for i in range(9):
        if board[i] is None:
            board[i] = ai_symbol
            score = _minimax(board, _other(ai_symbol), ai_symbol, 0, -1000, 1000)
            board[i] = None
            if score > best_score:
                best_score = score
                best_move = i
    return best_move


def get_ai_move(board: Board, ai_symbol: str, difficulty: str = "unbeatable") -> int:
    """
    Pick a move for the AI.

    difficulty:
      - "easy":       mostly random, rarely optimal
      - "medium":     optimal about half the time
      - "unbeatable": always optimal (classic minimax)
    """
    empty_cells = [i for i in range(9) if board[i] is None]
    if not empty_cells:
        raise ValueError("No empty cells left to play")

    if difficulty == "easy" and random.random() < 0.75:
        return random.choice(empty_cells)
    if difficulty == "medium" and random.random() < 0.5:
        return random.choice(empty_cells)

    return _best_move(list(board), ai_symbol)
