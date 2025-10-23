import os
import pickle
import time
from datetime import datetime


class Cache:
    """Simple pickle-based cache with expiration."""

    def __init__(self, path=".calends.pkl", expiration_seconds=60):
        self.path = path
        self.expiration = expiration_seconds
        self._data = {}
        self._load()

    def _load(self):
        """Load cache from pickle file if it exists."""
        if os.path.isfile(self.path):
            try:
                with open(self.path, "rb") as f:
                    self._data = pickle.load(f)
            except Exception:
                self._data = {}

    def _save(self):
        """Persist cache to pickle file."""
        try:
            with open(self.path, "wb") as f:
                pickle.dump(self._data, f)
        except Exception:
            pass  # Ignore save errors silently

    def get(self, key):
        """Return cached value if still valid."""
        entry = self._data.get(key)
        if not entry:
            return None
        timestamp = entry.get("timestamp")
        if time.time() - timestamp > self.expiration:
            # Expired
            self._data.pop(key, None)
            return None
        return entry.get("content")

    def set(self, key, content):
        """Cache new content."""
        self._data[key] = {"timestamp": time.time(), "content": content}
        self._save()
