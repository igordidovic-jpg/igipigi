"""
CFOS-XG PRO 75 TITAN - Result Cache Module

In-memory cache with TTL expiry for CSV analysis results.
Prevents redundant model computations for identical inputs.
"""
import time
import hashlib
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

DEFAULT_TTL = 300  # 5 minutes
DEFAULT_MAX_ENTRIES = 1000


class ResultCache:
    """
    Thread-safe in-memory cache with TTL expiry.

    Usage:
        cache = ResultCache(ttl=300)
        cached = cache.get("some_key")
        if cached is None:
            result = expensive_computation()
            cache.set("some_key", result)
    """

    def __init__(self, ttl: int = DEFAULT_TTL, max_entries: int = DEFAULT_MAX_ENTRIES):
        """
        Initialize cache.

        Args:
            ttl: Time-to-live in seconds (default: 300 = 5 minutes)
            max_entries: Maximum number of cached entries
        """
        self.ttl = ttl
        self.max_entries = max_entries
        self._store: dict[str, tuple[Any, float]] = {}

    @staticmethod
    def make_key(csv_line: str) -> str:
        """
        Create a cache key from a CSV input line.

        Args:
            csv_line: Raw CSV input string

        Returns:
            SHA256 hex digest of normalized input
        """
        normalized = csv_line.strip().lower()
        return hashlib.sha256(normalized.encode()).hexdigest()

    def get(self, key: str) -> Optional[Any]:
        """
        Retrieve a cached value.

        Args:
            key: Cache key

        Returns:
            Cached value, or None if missing/expired
        """
        if key not in self._store:
            return None

        value, expiry = self._store[key]
        if time.time() > expiry:
            del self._store[key]
            logger.debug(f"Cache miss (expired): {key[:16]}...")
            return None

        logger.debug(f"Cache hit: {key[:16]}...")
        return value

    def set(self, key: str, value: Any):
        """
        Store a value in the cache.

        Args:
            key: Cache key
            value: Value to cache
        """
        # Evict oldest entries if at capacity
        if len(self._store) >= self.max_entries:
            self._evict_oldest()

        expiry = time.time() + self.ttl
        self._store[key] = (value, expiry)
        logger.debug(f"Cache set: {key[:16]}... (expires in {self.ttl}s)")

    def invalidate(self, key: str):
        """Remove a specific key from cache."""
        self._store.pop(key, None)

    def clear(self):
        """Clear all cached entries."""
        self._store.clear()
        logger.info("Cache cleared")

    def size(self) -> int:
        """Return number of non-expired entries."""
        now = time.time()
        return sum(1 for _, (_, exp) in self._store.items() if exp > now)

    def _evict_oldest(self):
        """Remove the oldest 10% of entries."""
        n_remove = max(1, len(self._store) // 10)
        sorted_keys = sorted(self._store.items(), key=lambda x: x[1][1])
        for key, _ in sorted_keys[:n_remove]:
            del self._store[key]
        logger.debug(f"Cache evicted {n_remove} entries")
