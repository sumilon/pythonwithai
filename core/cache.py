"""
core/cache.py
Thread-safe in-memory TTL cache with bounded size (LRU eviction).
No external dependencies.
"""
import threading
import time
from collections import OrderedDict
from typing import Any


class TTLCache:
    """
    Thread-safe TTL cache with a hard cap on the number of entries.

    Eviction policy: LRU — when the cap is reached, the entry that was
    accessed least recently is removed to make room for the new one.
    Expired entries are also lazily removed on every read/write.
    """

    def __init__(self, default_ttl: int = 300, maxsize: int = 200) -> None:
        # OrderedDict preserves insertion/access order for LRU tracking
        self._store: OrderedDict[str, tuple[Any, float]] = OrderedDict()
        self._lock    = threading.Lock()
        self._ttl     = default_ttl
        self._maxsize = maxsize

    def get(self, key: str) -> Any:
        with self._lock:
            if key not in self._store:
                return None
            value, expiry = self._store[key]
            if time.monotonic() > expiry:
                del self._store[key]
                return None
            # Move to end = mark as most recently used
            self._store.move_to_end(key)
            return value

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        expiry = time.monotonic() + (ttl if ttl is not None else self._ttl)
        with self._lock:
            if key in self._store:
                self._store.move_to_end(key)
            self._store[key] = (value, expiry)
            # Evict LRU entry if over capacity
            while len(self._store) > self._maxsize:
                self._store.popitem(last=False)

    def delete(self, key: str) -> bool:
        """Remove a single entry by key. Returns True if it existed."""
        with self._lock:
            if key in self._store:
                del self._store[key]
                return True
            return False

    def clear(self) -> None:
        with self._lock:
            self._store.clear()

    def size(self) -> int:
        with self._lock:
            return len(self._store)
