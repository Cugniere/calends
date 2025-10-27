"""Simple file-based caching with expiration support."""

import os
import pickle
import time
import hashlib
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

    def set(self, key: str, content: Any, metadata: Optional[dict] = None) -> None:
        """
        Cache new content with current timestamp and optional metadata.

        Args:
            key: Cache key to store under
            content: Content to cache (must be picklable)
            metadata: Optional metadata (e.g., ETag, Last-Modified, content hash)
        """
        entry = {
            "timestamp": time.time(),
            "content": content,
        }

        # Store content hash for change detection
        if isinstance(content, str):
            entry["content_hash"] = hashlib.sha256(content.encode()).hexdigest()

        # Store HTTP metadata if provided
        if metadata:
            entry["metadata"] = metadata

        self._data[key] = entry
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

    def get_metadata(self, key: str) -> Optional[dict]:
        """
        Get metadata for a cached item without checking expiration.

        Args:
            key: Cache key to retrieve metadata for

        Returns:
            Metadata dictionary or None if not found
        """
        entry = self._data.get(key)
        if not entry:
            return None
        return entry.get("metadata")

    def get_content_hash(self, key: str) -> Optional[str]:
        """
        Get content hash for a cached item.

        Args:
            key: Cache key to retrieve hash for

        Returns:
            Content hash (SHA256) or None if not found
        """
        entry = self._data.get(key)
        if not entry:
            return None
        return entry.get("content_hash")

    def has_changed(self, key: str, new_content: str) -> bool:
        """
        Check if content has changed compared to cached version.

        Args:
            key: Cache key to check
            new_content: New content to compare

        Returns:
            True if content has changed or not in cache, False otherwise
        """
        old_hash = self.get_content_hash(key)
        if not old_hash:
            return True

        new_hash = hashlib.sha256(new_content.encode()).hexdigest()
        return old_hash != new_hash
