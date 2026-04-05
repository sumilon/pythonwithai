"""
core/cache.py
Thread-safe in-memory TTL cache. No external dependencies.
"""
import threading
import time
from typing import Any


class TTLCache:
    def __init__(self, default_ttl: int = 300) -> None:
        self._store: dict[str, tuple[Any, float]] = {}
        self._lock  = threading.Lock()
        self._ttl   = default_ttl

    def get(self, key: str) -> Any:
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            value, expiry = entry
            if time.monotonic() > expiry:
                del self._store[key]
                return None
            return value

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        expiry = time.monotonic() + (ttl if ttl is not None else self._ttl)
        with self._lock:
            self._store[key] = (value, expiry)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()


# Shared instances — quotes: 5 min TTL, history: 30 min TTL
quote_cache   = TTLCache(default_ttl=300)
history_cache = TTLCache(default_ttl=1800)