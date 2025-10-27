"""Pure iCal parsing logic without I/O or state management."""

import re
import sys
from datetime import datetime, timedelta, timezone
from typing import Optional, Any
from .constants import (
    DEFAULT_MAX_RECURRING_INSTANCES,
    DEFAULT_EVENT_DURATION_HOURS,
)

EventDict = dict[str, Any]


class ICalParser:
    """
    Pure iCal parser focused on parsing logic only.

    Handles parsing of iCal format including events, datetimes, and recurrence rules.
    Does not handle I/O, caching, or state management.

    Attributes:
        target_timezone: Optional timezone for converting event times
    """

    def __init__(self, target_timezone: Optional[timezone] = None) -> None:
        """
        Initialize the parser.

        Args:
            target_timezone: Optional timezone to convert event times to
        """
        self.target_timezone: Optional[timezone] = target_timezone

    def unfold_lines(self, content: str) -> list[str]:
        """
        Unfold iCal lines that are split with CRLF + space/tab.

        The iCal format allows long lines to be folded by inserting
        a newline followed by a space or tab.

        Args:
            content: Raw iCal content

        Returns:
            List of unfolded lines

        Raises:
            ValueError: If content is not a string
        """
        if not isinstance(content, str):
            raise ValueError("Content must be a string")

        if not content.strip():
            return []

        try:
            lines = content.replace("\r\n", "\n").replace("\r", "\n").split("\n")
            unfolded: list[str] = []
            current = ""
            for line in lines:
                if line and line[0] in (" ", "\t"):
                    current += line[1:]
                else:
                    if current:
                        unfolded.append(current)
                    current = line
            if current:
                unfolded.append(current)
            return unfolded
        except Exception as e:
            raise ValueError(f"Failed to unfold lines: {e}")

    def parse_datetime(self, dt_string: str) -> Optional[datetime]:
        """
        Parse an iCal datetime string into a Python datetime object.

        Supports multiple formats:
        - YYYYMMDDTHHMMSSZ (UTC)
        - YYYYMMDDTHHMMSS (local/floating)
        - YYYYMMDD (date only)

        Args:
            dt_string: iCal datetime string, may include property parameters

        Returns:
            Parsed datetime object, or None if parsing fails
        """
        if not dt_string or not isinstance(dt_string, str):
            return None

        try:
            dt_string = dt_string.strip()
            if ";" in dt_string or ":" in dt_string:
                dt_string = dt_string.split(":")[-1]

            if not dt_string:
                return None

            formats: list[tuple[str, bool]] = [
                ("%Y%m%dT%H%M%SZ", True),
                ("%Y%m%dT%H%M%S", False),
                ("%Y%m%d", False),
            ]
            dt: Optional[datetime] = None
            is_utc = False
            for fmt, utc_flag in formats:
                try:
                    dt = datetime.strptime(dt_string, fmt)
                    is_utc = utc_flag
                    break
                except ValueError:
                    continue

            if not dt:
                return None

            if is_utc:
                dt = dt.replace(tzinfo=timezone.utc)
            if self.target_timezone and dt.tzinfo:
                dt = dt.astimezone(self.target_timezone)
            return dt
        except Exception as e:
            print(
                f"Warning: Failed to parse datetime '{dt_string}': {e}", file=sys.stderr
            )
            return None

    def parse_rrule(self, rrule_line: str) -> Optional[dict[str, str]]:
        """
        Parse an iCal RRULE (recurrence rule) string.

        Args:
            rrule_line: RRULE line from iCal file (e.g., "RRULE:FREQ=DAILY;COUNT=10")

        Returns:
            Dictionary of rule components, or None if not a valid RRULE
        """
        if not rrule_line.startswith("RRULE:"):
            return None

        rrule_str = rrule_line[6:]
        rules: dict[str, str] = {}
        for part in rrule_str.split(";"):
            if "=" in part:
                key, value = part.split("=", 1)
                rules[key] = value
        return rules

    def parse_event(self, lines: list[str]) -> EventDict:
        """
        Parse iCal event lines into an event dictionary.

        Args:
            lines: List of property lines from a VEVENT component

        Returns:
            Event dictionary with parsed properties
        """
        event: EventDict = {
            "summary": "Untitled Event",
            "start": None,
            "end": None,
            "location": "",
            "description": "",
            "rrule": None,
        }
        for line in lines:
            if line.startswith("SUMMARY:"):
                event["summary"] = line[8:]
            elif line.startswith("DTSTART"):
                event["start"] = self.parse_datetime(line)
            elif line.startswith("DTEND"):
                event["end"] = self.parse_datetime(line)
            elif line.startswith("LOCATION:"):
                event["location"] = line[9:]
            elif line.startswith("DESCRIPTION:"):
                event["description"] = line[12:]
            elif line.startswith("RRULE:"):
                event["rrule"] = self.parse_rrule(line)

        if event["start"] and not event["start"].tzinfo:
            event["start"] = event["start"].replace(tzinfo=self.target_timezone)
        if event["end"] and not event["end"].tzinfo:
            event["end"] = event["end"].replace(tzinfo=self.target_timezone)

        if event["start"] and not event["end"]:
            event["end"] = event["start"] + timedelta(
                hours=DEFAULT_EVENT_DURATION_HOURS
            )

        return event

    def expand_recurring_event(
        self,
        event: EventDict,
        rrule: dict[str, str],
        max_instances: int = DEFAULT_MAX_RECURRING_INSTANCES,
    ) -> list[EventDict]:
        """
        Generate individual instances of a recurring event.

        Supports DAILY, WEEKLY, MONTHLY, and YEARLY frequencies with
        INTERVAL, COUNT, and UNTIL parameters.

        Args:
            event: Base event dictionary
            rrule: Parsed recurrence rule
            max_instances: Maximum number of instances to generate

        Returns:
            List of event instances
        """
        if not rrule or not event["start"]:
            return [event]

        try:
            freq = rrule.get("FREQ")
            if not freq or freq not in ["DAILY", "WEEKLY", "MONTHLY", "YEARLY"]:
                print(
                    f"Warning: Unsupported or missing FREQ in RRULE: {freq}",
                    file=sys.stderr,
                )
                return [event]

            try:
                count = int(rrule.get("COUNT", max_instances))
                if count <= 0:
                    count = max_instances
            except (ValueError, TypeError):
                print(
                    f"Warning: Invalid COUNT in RRULE, using default", file=sys.stderr
                )
                count = max_instances

            try:
                interval = int(rrule.get("INTERVAL", 1))
                if interval <= 0:
                    interval = 1
            except (ValueError, TypeError):
                print(f"Warning: Invalid INTERVAL in RRULE, using 1", file=sys.stderr)
                interval = 1

            until = rrule.get("UNTIL")
            until_dt: Optional[datetime] = None
            if until:
                until_dt = self.parse_datetime(until)

            instances: list[EventDict] = []
            current_start: datetime = event["start"]
            duration: timedelta = (
                event["end"] - event["start"]
                if event["end"]
                else timedelta(hours=DEFAULT_EVENT_DURATION_HOURS)
            )

            for i in range(min(count, max_instances)):
                if until_dt and current_start > until_dt:
                    break

                instance = event.copy()
                instance["start"] = current_start
                instance["end"] = current_start + duration
                instances.append(instance)

                try:
                    if freq == "DAILY":
                        current_start += timedelta(days=interval)
                    elif freq == "WEEKLY":
                        current_start += timedelta(weeks=interval)
                    elif freq == "MONTHLY":
                        month = current_start.month + interval
                        year = current_start.year + (month - 1) // 12
                        month = ((month - 1) % 12) + 1
                        try:
                            current_start = current_start.replace(
                                year=year, month=month
                            )
                        except ValueError:
                            import calendar

                            last_day = calendar.monthrange(year, month)[1]
                            current_start = current_start.replace(
                                year=year, month=month, day=last_day
                            )
                    elif freq == "YEARLY":
                        try:
                            current_start = current_start.replace(
                                year=current_start.year + interval
                            )
                        except ValueError:
                            current_start = current_start.replace(
                                year=current_start.year + interval, day=28
                            )
                except (ValueError, OverflowError) as e:
                    print(
                        f"Warning: Failed to generate recurrence instance: {e}",
                        file=sys.stderr,
                    )
                    break

            return instances
        except Exception as e:
            print(f"Warning: Failed to expand recurring event: {e}", file=sys.stderr)
            return [event]

    def parse_ical_content(self, content: str) -> list[EventDict]:
        """
        Parse complete iCal content into a list of events.

        Args:
            content: Raw iCal file content

        Returns:
            List of parsed and expanded event dictionaries

        Raises:
            ValueError: If content is invalid or not iCal format
        """
        if not content or not isinstance(content, str):
            raise ValueError("Content must be a non-empty string")

        if "BEGIN:VCALENDAR" not in content:
            raise ValueError(
                "Content does not contain BEGIN:VCALENDAR - not valid iCal format"
            )

        try:
            lines = self.unfold_lines(content)
            events: list[EventDict] = []
            in_event = False
            event_lines: list[str] = []

            for line in lines:
                if line == "BEGIN:VEVENT":
                    in_event, event_lines = True, []
                elif line == "END:VEVENT":
                    if event_lines:
                        try:
                            event = self.parse_event(event_lines)
                            if event["start"]:
                                if event.get("rrule"):
                                    instances = self.expand_recurring_event(
                                        event, event["rrule"]
                                    )
                                    events.extend(instances)
                                else:
                                    events.append(event)
                            else:
                                print(
                                    f"Warning: Skipping event without start time: {event.get('summary', 'Untitled')}",
                                    file=sys.stderr,
                                )
                        except Exception as e:
                            print(
                                f"Warning: Failed to parse event: {e}", file=sys.stderr
                            )
                    in_event = False
                elif in_event:
                    event_lines.append(line)

            if in_event:
                print("Warning: Unclosed VEVENT block at end of file", file=sys.stderr)

            return events
        except ValueError:
            raise
        except Exception as e:
            raise ValueError(f"Failed to parse iCal content: {e}")
