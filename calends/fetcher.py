"""Handles fetching iCal content from URLs and files with caching."""

import sys
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
