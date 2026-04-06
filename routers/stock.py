"""
routers/stock.py — stock page + JSON API endpoints
"""
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import HTMLResponse

from core.deps import templates
from services import stock as svc
from services.stock import validate_symbol

router = APIRouter()


@router.get("/stock", response_class=HTMLResponse, include_in_schema=False)
async def stock_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("stock.html", {"request": request})


@router.get("/api/quote/{symbol}", tags=["Stock"])
async def api_quote(symbol: str) -> dict:
    """
    Live stock quote — cached 5 min.
    NSE India: RELIANCE.NS | BSE India: RELIANCE.BO | US: AAPL | Index: ^NSEI
    """
    try:
        sym = validate_symbol(symbol)
        return await svc.get_quote(sym)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to fetch stock data.")


@router.get("/api/history/{symbol}", tags=["Stock"])
async def api_history(
        symbol: str,
        period: str = Query("1y", pattern="^(1mo|3mo|6mo|1y|2y|5y)$"),
) -> dict:
    """
    OHLCV price history with MA20/MA50 — cached 30 min.
    period: 1mo | 3mo | 6mo | 1y | 2y | 5y
    """
    try:
        sym = validate_symbol(symbol)
        return await svc.get_history(sym, period)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to fetch historical data.")
