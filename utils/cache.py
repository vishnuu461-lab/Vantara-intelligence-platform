# ============================================================
# utils/cache.py — Simple In-Memory TTL Cache
# ============================================================
# Caches ML prediction results in memory for a short period
# so repeated requests don't recompute everything from scratch.
#
# TTL = 120 seconds (2 minutes) by default.
# Auto-clears on server restart.
# No extra dependencies — pure Python dict + timestamps.
# ============================================================

import time
import threading

_cache: dict = {}
_lock = threading.Lock()

DEFAULT_TTL = 120  # seconds


def cache_get(key: str):
    """Return cached value if not expired, else None."""
    with _lock:
        entry = _cache.get(key)
        if entry is None:
            return None
        value, expires_at = entry
        if time.time() > expires_at:
            del _cache[key]
            return None
        return value


def cache_set(key: str, value, ttl: int = DEFAULT_TTL):
    """Store value in cache with a TTL (seconds)."""
    with _lock:
        _cache[key] = (value, time.time() + ttl)


def cache_delete(key: str):
    """Remove a specific key from cache."""
    with _lock:
        _cache.pop(key, None)


def cache_clear():
    """Clear all cached entries."""
    with _lock:
        _cache.clear()


def cache_stats() -> dict:
    """Return cache size info."""
    with _lock:
        now = time.time()
        total = len(_cache)
        active = sum(1 for _, (_, exp) in _cache.items() if now <= exp)
        return {"total_keys": total, "active_keys": active}
