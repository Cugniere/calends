"""Simple file-based caching with expiration support."""

import os
import pickle
import time
from typing import Any, Optional
from .constants import DEFAULT_CACHE_PATH, DEFAULT_CACHE_EXPIRATION


class Cache:
    """
    Simple pickle-based cache with expiration.

    Stores key-value pairs with timestamps in a pickle file.
    Automatically handles expiration and file persistence.

    Attributes:
        path: File path for the cache storage
        expiration: Expiration time in seconds
    """

    def __init__(
        self,
        path: str = DEFAULT_CACHE_PATH,
        expiration_seconds: int = DEFAULT_CACHE_EXPIRATION,
    ) -> None:
        """
        Initialize the cache.

        Args:
            path: File path for cache storage
            expiration_seconds: How long cached items remain valid
        """
        self.path: str = path
        self.expiration: int = expiration_seconds
        self._data: dict[str, dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        """
        Load cache from pickle file if it exists.

        Silently handles errors by initializing empty cache.
        """
        if os.path.isfile(self.path):
            try:
                with open(self.path, "rb") as f:
                    self._data = pickle.load(f)
            except Exception:
                self._data = {}

    def _save(self) -> None:
        """
        Persist cache to pickle file.

        Silently handles errors to avoid disrupting cache operations.
        """
        try:
            with open(self.path, "wb") as f:
                pickle.dump(self._data, f)
        except Exception:
            pass

    def get(self, key: str) -> Optional[Any]:
        """
        Return cached value if still valid.

        Args:
            key: Cache key to retrieve

        Returns:
            Cached value if valid and unexpired, None otherwise
        """
        entry = self._data.get(key)
        if not entry:
            return None
        timestamp = entry.get("timestamp")
        if time.time() - timestamp > self.expiration:
            self._data.pop(key, None)
            return None
        return entry.get("content")

    def set(self, key: str, content: Any) -> None:
        """
        Cache new content with current timestamp.

        Args:
            key: Cache key to store under
            content: Content to cache (must be picklable)
        """
        self._data[key] = {"timestamp": time.time(), "content": content}
        self._save()
