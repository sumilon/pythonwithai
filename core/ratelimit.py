"""
core/ratelimit.py
Lightweight in-process sliding-window rate limiter.

No external dependencies (no Redis, no slowapi).
Works per real client IP, respecting X-Forwarded-For when the app sits
behind a trusted reverse proxy (Cloud Run, nginx, etc.).

Usage in main.py:
    from core.ratelimit import RateLimitMiddleware
    app.add_middleware(RateLimitMiddleware, calls=5, period=60)
"""
from __future__ import annotations

import time
import threading
from collections import defaultdict, deque
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

# Paths that are always exempt from rate limiting.
# Add health / static asset paths here.
_EXEMPT_PREFIXES: tuple[str, ...] = ("/health", "/static")


def _real_ip(request: Request) -> str:
    """
    Extract the real client IP.

    Cloud Run (and most reverse proxies) set X-Forwarded-For.
    We take the *first* entry — the original client — not the last hop.
    Fall back to the direct connection IP when the header is absent.
    """
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Sliding-window rate limiter keyed by client IP.

    Parameters
    ----------
    calls  : maximum number of requests allowed per *period* seconds.
    period : window length in seconds (default 60).

    When the limit is exceeded the middleware returns HTTP 429 with a
    Retry-After header so well-behaved clients can back off automatically.
    """

    def __init__(self, app: ASGIApp, calls: int = 5, period: int = 60) -> None:
        super().__init__(app)
        self._calls  = calls
        self._period = period
        # IP → deque of request timestamps (monotonic seconds)
        self._windows: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def _is_rate_limited(self, ip: str) -> tuple[bool, int]:
        """
        Returns (limited, retry_after_seconds).
        Cleans up timestamps older than the window on every call.
        """
        now    = time.monotonic()
        cutoff = now - self._period

        with self._lock:
            dq = self._windows[ip]
            # Evict timestamps outside the current window
            while dq and dq[0] < cutoff:
                dq.popleft()

            if len(dq) >= self._calls:
                retry_after = int(self._period - (now - dq[0])) + 1
                return True, retry_after

            dq.append(now)
            return False, 0

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path

        # Exempt health checks and static assets
        if any(path.startswith(p) for p in _EXEMPT_PREFIXES):
            return await call_next(request)

        ip = _real_ip(request)
        limited, retry_after = self._is_rate_limited(ip)

        if limited:
            return JSONResponse(
                status_code=429,
                content={
                    "detail": (
                        f"Rate limit exceeded: max {self._calls} requests "
                        f"per {self._period} seconds. Please slow down."
                    )
                },
                headers={"Retry-After": str(retry_after)},
            )

        return await call_next(request)
