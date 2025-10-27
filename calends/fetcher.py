"""Handles fetching iCal content from URLs and files with caching."""

import sys
import asyncio
from concurrent.futures import ThreadPoolExecutor
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from typing import Optional
from .cache import Cache
from .constants import DEFAULT_CACHE_EXPIRATION, URL_FETCH_TIMEOUT
from .colors import Colors


class ICalFetcher:
    """
    Fetches iCal content from URLs or local files with caching support.

    Attributes:
        cache: Cache instance for storing fetched content
    """

    def __init__(
        self,
        cache_expiration: int = DEFAULT_CACHE_EXPIRATION,
        show_progress: bool = True,
    ) -> None:
        """
        Initialize the fetcher with cache.

        Args:
            cache_expiration: Cache expiration time in seconds
            show_progress: Whether to show progress indicators
        """
        self.cache: Cache = Cache(expiration_seconds=cache_expiration)
        self.show_progress: bool = show_progress

    def fetch_from_url(self, url: str) -> str:
        """
        Fetch iCal content from a URL with caching.

        Args:
            url: URL to fetch from

        Returns:
            The iCal content as a string

        Raises:
            ValueError: If URL is invalid
            TimeoutError: If request times out
            ConnectionError: If network connection fails
            Exception: For other HTTP or network errors
        """
        if not url or not (url.startswith("http://") or url.startswith("https://")):
            raise ValueError(f"Invalid URL: {url}")

        cached = self.cache.get(url)
        if cached:
            if self.show_progress:
                print(f"{Colors.DIM}  (cached){Colors.RESET}", file=sys.stderr)
            return cached

        if self.show_progress:
            print(
                f"{Colors.BLUE}Fetching {url}...{Colors.RESET}",
                end="",
                file=sys.stderr,
                flush=True,
            )

        try:
            req = Request(url, headers={"User-Agent": "calends/1.0"})
            with urlopen(req, timeout=URL_FETCH_TIMEOUT) as response:
                if response.status != 200:
                    raise Exception(f"HTTP {response.status}: Unexpected response")

                content = response.read().decode("utf-8")

                if not content.strip():
                    raise ValueError(f"Empty response from {url}")

                if "BEGIN:VCALENDAR" not in content:
                    raise ValueError(
                        f"Response does not appear to be valid iCal format"
                    )

                self.cache.set(url, content)

                return content
        except HTTPError as e:
            if self.show_progress:
                print(f" {Colors.RED}✗{Colors.RESET}", file=sys.stderr)
            if e.code == 404:
                raise Exception(f"Calendar not found (404): {url}")
            elif e.code == 403:
                raise Exception(f"Access forbidden (403): {url}")
            elif e.code == 401:
                raise Exception(f"Authentication required (401): {url}")
            else:
                raise Exception(f"HTTP Error {e.code}: {e.reason}")
        except URLError as e:
            if self.show_progress:
                print(f" {Colors.RED}✗{Colors.RESET}", file=sys.stderr)
            if "timed out" in str(e.reason).lower():
                raise TimeoutError(
                    f"Request timed out after {URL_FETCH_TIMEOUT}s: {url}"
                )
            else:
                raise ConnectionError(f"Network error: {e.reason}")
        except UnicodeDecodeError as e:
            if self.show_progress:
                print(f" {Colors.RED}✗{Colors.RESET}", file=sys.stderr)
            raise Exception(f"Invalid text encoding in response: {e}")
        except TimeoutError:
            if self.show_progress:
                print(f" {Colors.RED}✗{Colors.RESET}", file=sys.stderr)
            raise
        except ValueError:
            if self.show_progress:
                print(f" {Colors.RED}✗{Colors.RESET}", file=sys.stderr)
            raise
        except ConnectionError:
            if self.show_progress:
                print(f" {Colors.RED}✗{Colors.RESET}", file=sys.stderr)
            raise
        except Exception as e:
            if self.show_progress:
                print(f" {Colors.RED}✗{Colors.RESET}", file=sys.stderr)
            raise Exception(f"Failed to fetch {url}: {str(e)}")

    def fetch(self, source: str) -> Optional[str]:
        """
        Fetch iCal content from either a URL or local file.

        Args:
            source: URL or file path to fetch from

        Returns:
            The iCal content as a string, or None if fetching fails
        """
        if not source or not source.strip():
            print("Error: Empty source provided", file=sys.stderr)
            return None

        try:
            if source.startswith("http://") or source.startswith("https://"):
                return self.fetch_from_url(source)
            else:
                try:
                    with open(source, "r", encoding="utf-8") as f:
                        content = f.read()

                    if not content.strip():
                        print(f"Error: File is empty: {source}", file=sys.stderr)
                        return None

                    if "BEGIN:VCALENDAR" not in content:
                        print(
                            f"Error: File does not appear to be valid iCal format: {source}",
                            file=sys.stderr,
                        )
                        return None

                    return content
                except FileNotFoundError:
                    print(f"Error: File not found: {source}", file=sys.stderr)
                    return None
                except PermissionError:
                    print(f"Error: Permission denied: {source}", file=sys.stderr)
                    return None
                except UnicodeDecodeError:
                    print(
                        f"Error: File is not valid UTF-8 text: {source}",
                        file=sys.stderr,
                    )
                    return None
                except IsADirectoryError:
                    print(
                        f"Error: Path is a directory, not a file: {source}",
                        file=sys.stderr,
                    )
                    return None
        except Exception as e:
            print(f"Error reading {source}: {e}", file=sys.stderr)
            return None

    async def fetch_url_async(
        self, url: str
    ) -> tuple[str, Optional[str], Optional[str]]:
        """
        Async wrapper for fetch_from_url.

        Args:
            url: URL to fetch from

        Returns:
            Tuple of (url, content, error_message)
        """
        loop = asyncio.get_event_loop()
        try:
            content = await loop.run_in_executor(None, self.fetch_from_url, url)
            return (url, content, None)
        except Exception as e:
            return (url, None, str(e))

    def fetch_multiple(self, sources: list[str]) -> dict[str, Optional[str]]:
        """
        Fetch multiple sources in parallel (URLs only).

        File sources are fetched synchronously. URL sources are fetched
        in parallel using async operations for better performance.

        Args:
            sources: List of URLs or file paths

        Returns:
            Dictionary mapping source to content (None if fetch failed)
        """
        url_sources = [
            s for s in sources if s.startswith("http://") or s.startswith("https://")
        ]
        file_sources = [s for s in sources if s not in url_sources]

        results = {}

        # Fetch files synchronously (they're fast anyway)
        for source in file_sources:
            results[source] = self.fetch(source)

        # Fetch URLs in parallel if there are any
        if url_sources:
            try:
                # Check if any URLs are cached
                urls_to_fetch = []
                for url in url_sources:
                    cached = self.cache.get(url)
                    if cached:
                        results[url] = cached
                        if self.show_progress:
                            print(
                                f"{Colors.BLUE}Loading {url}...{Colors.RESET} {Colors.DIM}(cached){Colors.RESET}",
                                file=sys.stderr,
                            )
                    else:
                        urls_to_fetch.append(url)

                # Fetch non-cached URLs in parallel
                if urls_to_fetch:
                    if self.show_progress and len(urls_to_fetch) > 1:
                        print(
                            f"{Colors.BOLD}Fetching {len(urls_to_fetch)} URLs...{Colors.RESET}",
                            file=sys.stderr,
                        )

                    # Run async fetches
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        tasks = [self.fetch_url_async(url) for url in urls_to_fetch]
                        fetch_results = loop.run_until_complete(asyncio.gather(*tasks))

                        for url, content, error in fetch_results:
                            if error:
                                results[url] = None
                            else:
                                results[url] = content
                    finally:
                        loop.close()
            except Exception as e:
                # Fallback to sequential fetching
                if self.show_progress:
                    print(
                        f"{Colors.YELLOW}Warning: Parallel fetching failed, falling back to sequential{Colors.RESET}",
                        file=sys.stderr,
                    )
                for url in urls_to_fetch:
                    results[url] = self.fetch(url)

        return results
