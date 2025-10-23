"""Coordinates fetching, parsing, and managing calendar events."""

from datetime import timezone
from typing import Optional
from .parser import ICalParser
from .fetcher import ICalFetcher
from .event_collection import EventCollection
from .constants import DEFAULT_CACHE_EXPIRATION


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
    ) -> None:
        """
        Initialize the calendar manager.

        Args:
            target_timezone: Optional timezone to convert event times to
            cache_expiration: Cache expiration time in seconds
        """
        self.parser: ICalParser = ICalParser(target_timezone)
        self.fetcher: ICalFetcher = ICalFetcher(cache_expiration)
        self.events: EventCollection = EventCollection()

    def load_source(self, source: str) -> None:
        """
        Load events from a single calendar source.

        Args:
            source: URL or file path to calendar source
        """
        content = self.fetcher.fetch(source)
        if content:
            parsed_events = self.parser.parse_ical_content(content)
            self.events.add_events(parsed_events)
            self.events.expand_multiday_events()

    def load_sources(self, sources: list[str]) -> None:
        """
        Load events from multiple calendar sources.

        Args:
            sources: List of URLs or file paths to calendar sources
        """
        for source in sources:
            self.load_source(source)

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
