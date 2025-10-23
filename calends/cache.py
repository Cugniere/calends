import os
import pickle
import time
from typing import Any, Optional


class Cache:
    """Simple pickle-based cache with expiration."""

    def __init__(
        self, path: str = ".calends.pkl", expiration_seconds: int = 60
    ) -> None:
        self.path: str = path
        self.expiration: int = expiration_seconds
        self._data: dict[str, dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        """Load cache from pickle file if it exists."""
        if os.path.isfile(self.path):
            try:
                with open(self.path, "rb") as f:
                    self._data = pickle.load(f)
            except Exception:
                self._data = {}

    def _save(self) -> None:
        """Persist cache to pickle file."""
        try:
            with open(self.path, "wb") as f:
                pickle.dump(self._data, f)
        except Exception:
            pass

    def get(self, key: str) -> Optional[Any]:
        """Return cached value if still valid."""
        entry = self._data.get(key)
        if not entry:
            return None
        timestamp = entry.get("timestamp")
        if time.time() - timestamp > self.expiration:
            self._data.pop(key, None)
            return None
        return entry.get("content")

    def set(self, key: str, content: Any) -> None:
        """Cache new content."""
        self._data[key] = {"timestamp": time.time(), "content": content}
        self._save()
