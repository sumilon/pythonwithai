"""
services/stock.py
=================
Stock data via yfinance + curl_cffi browser impersonation.

IMPORTANT: Requires yfinance >= 0.2.50
yfinance 0.2.40 is completely broken on Python 3.13 — returns no data.
Fix: pip install --upgrade yfinance
"""
import asyncio
import logging
import math
from typing import Any

import yfinance as yf

from core.cache import TTLCache
from core.config import settings

logger = logging.getLogger(__name__)

# ── Cache instances (bounded LRU, sizes from settings) ────────────────────────
quote_cache   = TTLCache(default_ttl=settings.QUOTE_CACHE_TTL,   maxsize=settings.QUOTE_CACHE_MAX)
history_cache = TTLCache(default_ttl=settings.HISTORY_CACHE_TTL, maxsize=settings.HISTORY_CACHE_MAX)

# ── curl_cffi session ─────────────────────────────────────────────────────────
_SESSION = None
USE_CURL = False

try:
    from curl_cffi import requests as curl_requests
    _SESSION = curl_requests.Session(impersonate="chrome")
    USE_CURL = True
except Exception:
    pass

# ── Symbol validation ─────────────────────────────────────────────────────────
_SYM_CHARS = frozenset("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.^-")


def validate_symbol(symbol: str) -> str:
    sym = symbol.strip().upper()
    if not sym or len(sym) > 20 or not _SYM_CHARS.issuperset(sym):
        raise ValueError(
            f"Invalid symbol '{symbol}'. "
            "NSE India: TCS.NS | BSE India: TCS.BO | US: AAPL | Index: ^NSEI"
        )
    return sym


# ── Helpers ───────────────────────────────────────────────────────────────────

def _clean(val: Any) -> Any:
    """Recursively replace NaN/Inf with None for JSON safety."""
    if isinstance(val, float):
        if math.isnan(val) or math.isinf(val):
            return None
        return round(val, 6)
    if isinstance(val, dict):
        return {k: _clean(v) for k, v in val.items()}
    if isinstance(val, list):
        return [_clean(v) for v in val]
    return val


def _safe_get(obj: Any, attr: str) -> Any:
    """Safe attribute access — never raises, always returns clean value."""
    try:
        v = getattr(obj, attr, None)
        return _clean(v)
    except Exception:
        return None


def _get_ticker(symbol: str) -> yf.Ticker:
    if USE_CURL and _SESSION is not None:
        return yf.Ticker(symbol, session=_SESSION)
    return yf.Ticker(symbol)


# ── Field definitions ─────────────────────────────────────────────────────────

_FAST_KEYS = [
    "last_price", "previous_close", "open", "day_high", "day_low",
    "fifty_two_week_high", "fifty_two_week_low", "market_cap",
    "currency", "exchange", "quote_type", "last_volume",
    "ten_day_average_volume", "three_month_average_volume",
]

_INFO_KEYS = [
    "longName", "trailingPE", "forwardPE", "trailingEps", "forwardEps",
    "beta", "fiftyDayAverage", "twoHundredDayAverage",
    "marketCap", "enterpriseValue", "priceToBook",
    "priceToSalesTrailing12Months", "enterpriseToEbitda",
    "enterpriseToRevenue", "dividendRate", "dividendYield",
    "payoutRatio", "fiveYearAvgDividendYield", "earningsGrowth",
    "revenueGrowth", "pegRatio", "earningsQuarterlyGrowth",
    "fiftyTwoWeekHigh", "fiftyTwoWeekLow", "averageVolume",
    "floatShares", "totalRevenue", "grossProfits", "ebitda",
    "netIncomeToCommon", "grossMargins", "operatingMargins",
    "profitMargins", "ebitdaMargins", "operatingCashflow",
    "freeCashflow", "returnOnEquity", "returnOnAssets",
    "totalAssets", "totalDebt", "totalCash", "totalCashPerShare",
    "debtToEquity", "currentRatio", "quickRatio", "bookValue",
    "targetMeanPrice", "targetHighPrice", "targetLowPrice",
    "recommendationKey", "numberOfAnalystOpinions",
    "longBusinessSummary", "industry", "sector", "country",
    "website", "irWebsite", "address1", "city", "state",
    "phone", "fullTimeEmployees",
]


# ── Blocking fetches (run in executor) ────────────────────────────────────────

def _fetch_quote(symbol: str) -> dict:
    t    = _get_ticker(symbol)
    fi   = t.fast_info
    fast = {k: _safe_get(fi, k) for k in _FAST_KEYS}

    price = fast.get("last_price")
    if not price:
        raise ValueError(
            f"No price data for '{symbol}'. "
            "NSE India stocks need '.NS' suffix (e.g. TCS.NS, RELIANCE.NS). "
            "BSE stocks use '.BO'. Ensure yfinance is up to date: "
            "pip install --upgrade yfinance"
        )

    prev = fast.get("previous_close") or price
    info: dict = {}
    try:
        info = t.info or {}
    except Exception:
        pass

    return {
        "symbol":    symbol,
        "fast":      fast,
        "change":    _clean(price - prev),
        "changePct": _clean((price - prev) / prev * 100) if prev else 0.0,
        "info":      {k: _clean(info.get(k)) for k in _INFO_KEYS},
    }


def _fetch_history(symbol: str, period: str) -> dict:
    t    = _get_ticker(symbol)
    hist = t.history(period=period)

    if hist.empty:
        raise ValueError(
            f"No historical data for '{symbol}' (period={period}). "
            "Verify the symbol and ensure yfinance is up to date."
        )

    dates   = [str(d)[:10] for d in hist.index]
    opens   = _clean(hist["Open"].tolist())
    highs   = _clean(hist["High"].tolist())
    lows    = _clean(hist["Low"].tolist())
    closes  = _clean(hist["Close"].tolist())
    volumes = _clean(hist["Volume"].tolist()) if "Volume" in hist.columns else []

    def _ma(n: int) -> list:
        series = hist["Close"].rolling(n).mean()
        return [None if math.isnan(v) else round(float(v), 4) for v in series]

    result = {
        "symbol":  symbol,
        "period":  period,
        "dates":   dates,
        "open":    opens,
        "high":    highs,
        "low":     lows,
        "close":   closes,
        "volume":  volumes,
        "ma20":    _ma(20) if len(hist) >= 20 else [],
        "ma50":    _ma(50) if len(hist) >= 50 else [],
    }
    del hist  # release DataFrame memory immediately
    return result


# ── Public async API ──────────────────────────────────────────────────────────

async def get_quote(symbol: str) -> dict:
    cached = quote_cache.get(symbol)
    if cached is not None:
        return cached
    # asyncio.to_thread is the modern replacement for get_event_loop().run_in_executor()
    result = await asyncio.to_thread(_fetch_quote, symbol)
    quote_cache.set(symbol, result)
    return result


async def get_history(symbol: str, period: str) -> dict:
    key = f"{symbol}:{period}"
    cached = history_cache.get(key)
    if cached is not None:
        return cached
    result = await asyncio.to_thread(_fetch_history, symbol, period)
    history_cache.set(key, result)
    return result
