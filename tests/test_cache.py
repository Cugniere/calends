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


class TestCacheMetadata:
    """Test cache metadata and change detection."""

    def test_set_with_metadata(self, temp_cache_dir):
        """Test storing content with metadata."""
        cache_path = temp_cache_dir / "metadata_test.pkl"
        cache = Cache(path=str(cache_path))
        content = "test content"
        metadata = {"etag": '"abc123"', "last_modified": "Wed, 21 Oct 2015 07:28:00 GMT"}

        cache.set("test_key", content, metadata)

        stored_metadata = cache.get_metadata("test_key")
        assert stored_metadata is not None
        assert stored_metadata["etag"] == '"abc123"'
        assert stored_metadata["last_modified"] == "Wed, 21 Oct 2015 07:28:00 GMT"

    def test_get_content_hash(self, temp_cache_dir):
        """Test content hash generation and retrieval."""
        cache_path = temp_cache_dir / "hash_test.pkl"
        cache = Cache(path=str(cache_path))
        content = "test content for hashing"

        cache.set("test_key", content)

        content_hash = cache.get_content_hash("test_key")
        assert content_hash is not None
        assert len(content_hash) == 64  # SHA256 hex digest length

    def test_has_changed_same_content(self, temp_cache_dir):
        """Test has_changed returns False for identical content."""
        cache_path = temp_cache_dir / "unchanged_test.pkl"
        cache = Cache(path=str(cache_path))
        content = "unchanged content"

        cache.set("test_key", content)

        assert not cache.has_changed("test_key", content)

    def test_has_changed_different_content(self, temp_cache_dir):
        """Test has_changed returns True for modified content."""
        cache_path = temp_cache_dir / "changed_test.pkl"
        cache = Cache(path=str(cache_path))
        original = "original content"
        modified = "modified content"

        cache.set("test_key", original)

        assert cache.has_changed("test_key", modified)

    def test_has_changed_no_cache(self, temp_cache_dir):
        """Test has_changed returns True when no cache exists."""
        cache_path = temp_cache_dir / "nocache_test.pkl"
        cache = Cache(path=str(cache_path))

        assert cache.has_changed("nonexistent_key", "any content")

    def test_get_metadata_nonexistent(self, temp_cache_dir):
        """Test get_metadata returns None for nonexistent key."""
        cache_path = temp_cache_dir / "nometa_test.pkl"
        cache = Cache(path=str(cache_path))

        assert cache.get_metadata("nonexistent_key") is None

    def test_get_content_hash_nonexistent(self, temp_cache_dir):
        """Test get_content_hash returns None for nonexistent key."""
        cache_path = temp_cache_dir / "nohash_test.pkl"
        cache = Cache(path=str(cache_path))

        assert cache.get_content_hash("nonexistent_key") is None
