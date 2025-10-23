import pytest
import time
from pathlib import Path
from calends.cache import Cache


class TestCache:
    def test_set_and_get(self, temp_cache_dir):
        cache = Cache(str(temp_cache_dir / "test.cache"), expiration_seconds=3600)

        cache.set("test_key", "test_data")
        result = cache.get("test_key")

        assert result == "test_data"

    def test_get_expired(self, temp_cache_dir):
        cache = Cache(str(temp_cache_dir / "test.cache"), expiration_seconds=1)

        cache.set("test_key", "test_data")
        time.sleep(2)
        result = cache.get("test_key")

        assert result is None

    def test_get_nonexistent(self, temp_cache_dir):
        cache = Cache(str(temp_cache_dir / "nonexistent.cache"))

        result = cache.get("nonexistent_key")

        assert result is None

    def test_get_valid_within_expiry(self, temp_cache_dir):
        cache = Cache(str(temp_cache_dir / "test.cache"), expiration_seconds=10)

        cache.set("test_key", "valid_data")
        time.sleep(1)
        result = cache.get("test_key")

        assert result == "valid_data"

    def test_overwrite_cache(self, temp_cache_dir):
        cache = Cache(str(temp_cache_dir / "test.cache"), expiration_seconds=3600)

        cache.set("test_key", "first")
        cache.set("test_key", "second")
        result = cache.get("test_key")

        assert result == "second"

    def test_cache_file_created(self, temp_cache_dir):
        cache_path = temp_cache_dir / "test.cache"
        cache = Cache(str(cache_path))

        cache.set("test_key", "data")

        assert cache_path.exists()
