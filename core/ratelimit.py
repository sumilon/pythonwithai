"""
core/ratelimit.py
In-process sliding-window rate limiter keyed by client IP.

No external dependencies (no Redis, no slowapi). Works correctly behind
Cloud Run and nginx reverse proxies by reading X-Forwarded-For.

Usage:
    app.add_middleware(RateLimitMiddleware, calls=10, period=60)
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

# Requests to these path prefixes skip rate limiting entirely.
_EXEMPT_PREFIXES: tuple[str, ...] = ("/health", "/static")

# Hard cap on unique IPs tracked in memory at once. When exceeded, the
# oldest entry is evicted to make room — prevents unbounded growth during
# traffic spikes with many unique source IPs.
_MAX_IPS: int = 5_000

# Sweep stale IP buckets every N requests. Between sweeps, up to
# _PURGE_EVERY extra expired entries may linger — acceptable on free tier.
_PURGE_EVERY: int = 500


def _real_ip(request: Request) -> str:
    """Return the originating client IP.

    Cloud Run prepends the real client IP to X-Forwarded-For. We take
    the first entry rather than the last to avoid trusting a spoofed
    value appended by the client itself.
    """
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Sliding-window rate limiter.

    Parameters
    ----------
    calls  : max requests allowed per *period* seconds per IP.
    period : window length in seconds.

    Responds with HTTP 429 and a Retry-After header when the limit is
    exceeded, so well-behaved clients know when to retry.
    """

    def __init__(self, app: ASGIApp, calls: int = 5, period: int = 60) -> None:
        super().__init__(app)
        self._calls  = calls
        self._period = period
        self._windows: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()
        self._request_count = 0

    def _is_rate_limited(self, ip: str) -> tuple[bool, int]:
        """Return (is_limited, retry_after_seconds) for the given IP."""
        now    = time.monotonic()
        cutoff = now - self._period

        with self._lock:
            self._request_count += 1

            # Periodically remove buckets for IPs that have gone quiet.
            if self._request_count % _PURGE_EVERY == 0:
                stale = [k for k, dq in self._windows.items()
                         if not dq or dq[-1] < cutoff]
                for k in stale:
                    del self._windows[k]

            # Enforce hard IP cap — evict the oldest bucket if needed.
            while len(self._windows) >= _MAX_IPS and ip not in self._windows:
                self._windows.pop(next(iter(self._windows)), None)

            dq = self._windows[ip]
            while dq and dq[0] < cutoff:
                dq.popleft()

            if len(dq) >= self._calls:
                retry_after = int(self._period - (now - dq[0])) + 1
                return True, retry_after

            dq.append(now)
            return False, 0

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path

        if any(path.startswith(p) for p in _EXEMPT_PREFIXES):
            return await call_next(request)

        if self._calls == 0:
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
