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
    ) -> None:
        """
        Initialize the calendar manager.

        Args:
            target_timezone: Optional timezone to convert event times to
            cache_expiration: Cache expiration time in seconds
            show_progress: Whether to show progress indicators
        """
        self.parser: ICalParser = ICalParser(target_timezone)
        self.fetcher: ICalFetcher = ICalFetcher(cache_expiration, show_progress)
        self.events: EventCollection = EventCollection()
        self.show_progress: bool = show_progress

    def load_source(self, source: str) -> None:
        """
        Load events from a single calendar source.

        Args:
            source: URL or file path to calendar source
        """
        is_url = source.startswith("http://") or source.startswith("https://")

        if self.show_progress and not is_url:
            source_display = source if len(source) <= 60 else "..." + source[-57:]
            print(f"{Colors.BLUE}Loading {source_display}...{Colors.RESET}", end="", file=sys.stderr, flush=True)

        initial_count = self.events.count()
        content = self.fetcher.fetch(source)

        if content:
            parsed_events = self.parser.parse_ical_content(content)
            self.events.add_events(parsed_events)
            self.events.expand_multiday_events()
            added_count = self.events.count() - initial_count

            if self.show_progress:
                if is_url:
                    print(f" {Colors.GREEN}✓{Colors.RESET} ({added_count} events)", file=sys.stderr)
                else:
                    print(f" {Colors.GREEN}✓{Colors.RESET} ({added_count} events)", file=sys.stderr)

    def load_sources(self, sources: list[str]) -> None:
        """
        Load events from multiple calendar sources.

        Args:
            sources: List of URLs or file paths to calendar sources
        """
        if self.show_progress and len(sources) > 1:
            print(f"{Colors.BOLD}Loading {len(sources)} calendar sources...{Colors.RESET}", file=sys.stderr)

        for source in sources:
            self.load_source(source)

        if self.show_progress and len(sources) > 1:
            print(f"{Colors.BOLD}Loaded {self.count_events()} total events{Colors.RESET}\n", file=sys.stderr)

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
