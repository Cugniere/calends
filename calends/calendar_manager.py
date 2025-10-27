"""Coordinates fetching, parsing, and managing calendar events."""

import sys
from datetime import timezone
from typing import Optional
from .parser import ICalParser
from .fetcher import ICalFetcher
from .event_collection import EventCollection
from .constants import DEFAULT_CACHE_EXPIRATION
from .colors import Colors


class CalendarManager:
    """
    High-level coordinator for loading and managing calendar events.

    Combines fetching, parsing, and event management into a single interface.
    This is the main class that should be used by applications.

    Attributes:
        parser: iCal parser instance
        fetcher: Content fetcher instance
        events: Event collection instance
    """

    def __init__(
        self,
        target_timezone: Optional[timezone] = None,
        cache_expiration: int = DEFAULT_CACHE_EXPIRATION,
        show_progress: bool = True,
        aliases: Optional[dict[str, str]] = None,
    ) -> None:
        """
        Initialize the calendar manager.

        Args:
            target_timezone: Optional timezone to convert event times to
            cache_expiration: Cache expiration time in seconds
            show_progress: Whether to show progress indicators
            aliases: Optional dict mapping source URL/path to friendly name
        """
        self.parser: ICalParser = ICalParser(target_timezone)
        self.fetcher: ICalFetcher = ICalFetcher(cache_expiration, show_progress)
        self.events: EventCollection = EventCollection()
        self.show_progress: bool = show_progress
        self.sources: list[str] = []
        self.aliases: dict[str, str] = aliases or {}

    def _get_display_name(self, source: str) -> str:
        """
        Get display name for a source (alias if available, otherwise truncated source).

        Args:
            source: Source URL or path

        Returns:
            Display name for the source
        """
        if source in self.aliases:
            return self.aliases[source]
        # Truncate long sources
        return source if len(source) <= 60 else "..." + source[-57:]

    def load_source(self, source: str) -> None:
        """
        Load events from a single calendar source.

        Args:
            source: URL or file path to calendar source
        """
        is_url = source.startswith("http://") or source.startswith("https://")
        source_display = self._get_display_name(source)

        if self.show_progress and not is_url:
            print(
                f"{Colors.BLUE}Loading {source_display}...{Colors.RESET}",
                end="",
                file=sys.stderr,
                flush=True,
            )

        initial_count = self.events.count()
        content = self.fetcher.fetch(source)

        if content:
            parsed_events = self.parser.parse_ical_content(content)
            self.events.add_events(parsed_events)
            self.events.expand_multiday_events()
            added_count = self.events.count() - initial_count

            if self.show_progress:
                if is_url:
                    print(
                        f" {Colors.GREEN}✓{Colors.RESET} ({added_count} events)",
                        file=sys.stderr,
                    )
                else:
                    print(
                        f" {Colors.GREEN}✓{Colors.RESET} ({added_count} events)",
                        file=sys.stderr,
                    )

    def load_sources(self, sources: list[str]) -> None:
        """
        Load events from multiple calendar sources.

        Uses parallel fetching for URLs to improve performance.

        Args:
            sources: List of URLs or file paths to calendar sources
        """
        self.sources = sources

        if self.show_progress and len(sources) > 1:
            print(
                f"{Colors.BOLD}Loading {len(sources)} calendar sources...{Colors.RESET}",
                file=sys.stderr,
            )

        # Check if we have multiple URLs that could benefit from parallel fetching
        url_sources = [
            s for s in sources if s.startswith("http://") or s.startswith("https://")
        ]

        if len(url_sources) > 1:
            # Use parallel fetching for multiple URLs
            all_contents = self.fetcher.fetch_multiple(sources, self.aliases)

            for source in sources:
                content = all_contents.get(source)
                if content:
                    is_url = source.startswith("http://") or source.startswith(
                        "https://"
                    )

                    initial_count = self.events.count()
                    parsed_events = self.parser.parse_ical_content(content)
                    self.events.add_events(parsed_events)
                    self.events.expand_multiday_events()
                    added_count = self.events.count() - initial_count

                    if self.show_progress:
                        source_display = self._get_display_name(source)
                        print(
                            f"{Colors.BLUE}{source_display}{Colors.RESET} {Colors.GREEN}✓{Colors.RESET} ({added_count} events)",
                            file=sys.stderr,
                        )
        else:
            # Use sequential loading for single URL or file-only sources
            for source in sources:
                self.load_source(source)

        if self.show_progress and len(sources) > 1:
            print(
                f"{Colors.BOLD}Loaded {self.count_events()} total events{Colors.RESET}\n",
                file=sys.stderr,
            )

    def reload_sources(self, force: bool = False) -> list[dict]:
        """
        Reload calendar sources, optionally checking for changes first.

        Args:
            force: If True, clear cache and force full reload.
                   If False, only reload sources that have changed.

        Returns:
            List of all loaded events after refresh
        """
        if force:
            # Clear cache to force fresh fetch
            self.fetcher.cache.clear()

            # Clear events
            self.events = EventCollection()

            # Reload all sources
            if self.sources:
                self.load_sources(self.sources)
        else:
            # Partial refresh - only reload changed sources
            if self.sources:
                all_contents, changed_sources = self.fetcher.refresh_if_changed(
                    self.sources
                )

                if changed_sources:
                    if self.show_progress:
                        print(
                            f"{Colors.CYAN}{len(changed_sources)} source(s) changed, reloading...{Colors.RESET}",
                            file=sys.stderr,
                        )

                    # Clear events and reload everything
                    # (easier than tracking which events came from which source)
                    self.events = EventCollection()

                    for source in self.sources:
                        content = all_contents.get(source)
                        if content:
                            parsed_events = self.parser.parse_ical_content(content)
                            self.events.add_events(parsed_events)

                    self.events.expand_multiday_events()

                    if self.show_progress:
                        print(
                            f"{Colors.GREEN}✓{Colors.RESET} Reloaded {self.count_events()} events",
                            file=sys.stderr,
                        )
                else:
                    if self.show_progress:
                        print(
                            f"{Colors.DIM}No changes detected{Colors.RESET}",
                            file=sys.stderr,
                        )

        return self.get_all_events()

    def get_all_events(self) -> list[dict]:
        """
        Get all loaded events.

        Returns:
            List of all event dictionaries
        """
        return self.events.events

    def count_events(self) -> int:
        """
        Get the total number of events.

        Returns:
            Number of loaded events
        """
        return self.events.count()
