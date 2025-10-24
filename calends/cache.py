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

    def clear(self) -> None:
        """
        Clear all cached data and remove the cache file.

        This completely empties the cache and deletes the cache file
        from the filesystem.
        """
        self._data = {}
        if os.path.isfile(self.path):
            try:
                os.remove(self.path)
            except Exception:
                pass

    def size(self) -> int:
        """
        Get the number of items in the cache.

        Returns:
            Number of cached entries (including expired ones)
        """
        return len(self._data)

    def get_stats(self) -> dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache stats including:
            - total_entries: Total number of cached items
            - valid_entries: Number of non-expired items
            - cache_file_exists: Whether cache file exists on disk
            - cache_path: Path to cache file
        """
        valid_count = 0
        now = time.time()
        for entry in self._data.values():
            timestamp = entry.get("timestamp", 0)
            if now - timestamp <= self.expiration:
                valid_count += 1

        return {
            "total_entries": len(self._data),
            "valid_entries": valid_count,
            "cache_file_exists": os.path.isfile(self.path),
            "cache_path": self.path,
        }

    def cleanup_expired(self) -> int:
        """
        Remove expired entries from the cache.

        Returns:
            Number of entries removed
        """
        now = time.time()
        expired_keys = []
        for key, entry in self._data.items():
            timestamp = entry.get("timestamp", 0)
            if now - timestamp > self.expiration:
                expired_keys.append(key)

        for key in expired_keys:
            self._data.pop(key, None)

        if expired_keys:
            self._save()

        return len(expired_keys)
