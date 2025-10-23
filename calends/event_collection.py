"""Manages collections of calendar events and their expansion."""

from datetime import datetime, timedelta, date
from typing import Any

EventDict = dict[str, Any]


class EventCollection:
    """
    Manages a collection of calendar events with support for expansion.

    Handles multi-day event splitting and provides filtering capabilities.

    Attributes:
        events: List of event dictionaries
    """

    def __init__(self) -> None:
        """Initialize an empty event collection."""
        self.events: list[EventDict] = []

    def add_event(self, event: EventDict) -> None:
        """
        Add a single event to the collection.

        Args:
            event: Event dictionary containing event data
        """
        self.events.append(event)

    def add_events(self, events: list[EventDict]) -> None:
        """
        Add multiple events to the collection.

        Args:
            events: List of event dictionaries
        """
        self.events.extend(events)

    def expand_multiday_events(self) -> None:
        """
        Expand multi-day events into separate daily events.

        Events spanning multiple days are split into one event per day,
        with appropriate start and end times for each day.
        """
        expanded: list[EventDict] = []
        for event in self.events:
            if not event["start"] or not event["end"]:
                expanded.append(event)
                continue

            start_date = event["start"].date()
            end_date = event["end"].date()

            if start_date == end_date:
                expanded.append(event)
                continue

            current_date = start_date
            while current_date < end_date:
                day_event = event.copy()

                if current_date == start_date:
                    day_event["start"] = event["start"]
                    next_midnight = datetime.combine(
                        current_date + timedelta(days=1), datetime.min.time()
                    )
                    if event["start"].tzinfo:
                        next_midnight = next_midnight.replace(
                            tzinfo=event["start"].tzinfo
                        )
                    day_event["end"] = next_midnight
                elif current_date == end_date - timedelta(days=1):
                    day_start = datetime.combine(current_date, datetime.min.time())
                    if event["start"].tzinfo:
                        day_start = day_start.replace(tzinfo=event["start"].tzinfo)
                    day_event["start"] = day_start
                    day_event["end"] = event["end"]
                else:
                    day_start = datetime.combine(current_date, datetime.min.time())
                    day_end = datetime.combine(
                        current_date + timedelta(days=1), datetime.min.time()
                    )
                    if event["start"].tzinfo:
                        day_start = day_start.replace(tzinfo=event["start"].tzinfo)
                        day_end = day_end.replace(tzinfo=event["start"].tzinfo)
                    day_event["start"] = day_start
                    day_event["end"] = day_end

                expanded.append(day_event)
                current_date += timedelta(days=1)

        self.events = expanded

    def filter_by_date_range(
        self, start_date: datetime, end_date: datetime
    ) -> list[EventDict]:
        """
        Filter events within a specific date range.

        Args:
            start_date: Start of the date range
            end_date: End of the date range

        Returns:
            List of events within the date range
        """
        return [
            event
            for event in self.events
            if event["start"] and start_date <= event["start"] < end_date
        ]

    def count(self) -> int:
        """
        Get the total number of events.

        Returns:
            Number of events in the collection
        """
        return len(self.events)

    def clear(self) -> None:
        """Clear all events from the collection."""
        self.events = []
