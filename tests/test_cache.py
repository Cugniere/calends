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


class TestCacheManagement:
    def test_clear_cache(self, temp_cache_dir):
        cache_path = temp_cache_dir / "test_clear.pkl"
        cache = Cache(path=str(cache_path))

        cache.set("key1", "value1")
        cache.set("key2", "value2")
        assert cache.size() == 2
        assert cache_path.exists()

        cache.clear()

        assert cache.size() == 0
        assert not cache_path.exists()

    def test_cache_size(self, temp_cache_dir):
        cache_path = temp_cache_dir / "test_size.pkl"
        cache = Cache(path=str(cache_path))

        assert cache.size() == 0

        cache.set("key1", "value1")
        assert cache.size() == 1

        cache.set("key2", "value2")
        assert cache.size() == 2

    def test_get_stats(self, temp_cache_dir):
        cache_path = temp_cache_dir / "test_stats.pkl"
        cache = Cache(path=str(cache_path), expiration_seconds=1)

        cache.set("key1", "value1")
        stats = cache.get_stats()

        assert stats["total_entries"] == 1
        assert stats["valid_entries"] == 1
        assert stats["cache_file_exists"] is True
        assert stats["cache_path"] == str(cache_path)

    def test_get_stats_with_expired(self, temp_cache_dir):
        cache_path = temp_cache_dir / "test_stats_expired.pkl"
        cache = Cache(path=str(cache_path), expiration_seconds=1)

        cache.set("key1", "value1")
        time.sleep(1.1)
        cache.set("key2", "value2")

        stats = cache.get_stats()

        assert stats["total_entries"] == 2
        assert stats["valid_entries"] == 1

    def test_cleanup_expired(self, temp_cache_dir):
        cache_path = temp_cache_dir / "test_cleanup.pkl"
        cache = Cache(path=str(cache_path), expiration_seconds=1)

        cache.set("key1", "value1")
        cache.set("key2", "value2")
        time.sleep(1.1)
        cache.set("key3", "value3")

        removed = cache.cleanup_expired()

        assert removed == 2
        assert cache.size() == 1
        assert cache.get("key3") == "value3"
        assert cache.get("key1") is None

    def test_clear_nonexistent_cache(self, temp_cache_dir):
        cache_path = temp_cache_dir / "nonexistent.pkl"
        cache = Cache(path=str(cache_path))

        cache.clear()

        assert cache.size() == 0
        assert not cache_path.exists()
