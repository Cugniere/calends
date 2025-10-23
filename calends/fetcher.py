"""Handles fetching iCal content from URLs and files with caching."""

import sys
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from typing import Optional
from .cache import Cache
from .constants import DEFAULT_CACHE_EXPIRATION, URL_FETCH_TIMEOUT


class ICalFetcher:
    """
    Fetches iCal content from URLs or local files with caching support.

    Attributes:
        cache: Cache instance for storing fetched content
    """

    def __init__(self, cache_expiration: int = DEFAULT_CACHE_EXPIRATION) -> None:
        """
        Initialize the fetcher with cache.

        Args:
            cache_expiration: Cache expiration time in seconds
        """
        self.cache: Cache = Cache(expiration_seconds=cache_expiration)

    def fetch_from_url(self, url: str) -> str:
        """
        Fetch iCal content from a URL with caching.

        Args:
            url: URL to fetch from

        Returns:
            The iCal content as a string

        Raises:
            Exception: If fetching fails due to HTTP or network errors
        """
        cached = self.cache.get(url)
        if cached:
            return cached

        try:
            req = Request(url, headers={"User-Agent": "iCal-Viewer/1.0"})
            with urlopen(req, timeout=URL_FETCH_TIMEOUT) as response:
                content = response.read().decode("utf-8")
                self.cache.set(url, content)
                return content
        except HTTPError as e:
            raise Exception(f"HTTP Error {e.code}: {e.reason}")
        except URLError as e:
            raise Exception(f"URL Error: {e.reason}")
        except Exception as e:
            raise Exception(f"Failed to fetch URL: {str(e)}")

    def fetch(self, source: str) -> Optional[str]:
        """
        Fetch iCal content from either a URL or local file.

        Args:
            source: URL or file path to fetch from

        Returns:
            The iCal content as a string, or None if fetching fails
        """
        try:
            if source.startswith("http://") or source.startswith("https://"):
                return self.fetch_from_url(source)
            else:
                with open(source, "r", encoding="utf-8") as f:
                    return f.read()
        except Exception as e:
            print(f"Error reading {source}: {e}", file=sys.stderr)
            return None
