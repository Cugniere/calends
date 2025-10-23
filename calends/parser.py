import sys
import re
from datetime import datetime, timedelta, timezone
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from typing import Optional, Any
from .cache import Cache

EventDict = dict[str, Any]


class ICalParser:
    """Parse iCal files from url"""

    def __init__(
        self, target_timezone: Optional[timezone] = None, cache_expiration: int = 60
    ) -> None:
        self.events: list[EventDict] = []
        self.target_timezone: Optional[timezone] = target_timezone
        self.cache: Cache = Cache(expiration_seconds=cache_expiration)

    def unfold_lines(self, content: str) -> list[str]:
        """Unfold lines that are split with CRLF + space/tab."""
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

    def parse_datetime(self, dt_string: str) -> Optional[datetime]:
        if not dt_string:
            return None
        if ";" in dt_string or ":" in dt_string:
            dt_string = dt_string.split(":")[-1]
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

    def parse_event(self, lines: list[str]) -> EventDict:
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
            event["end"] = event["start"] + timedelta(hours=1)

        return event

    def parse_rrule(self, rrule_line: str) -> Optional[dict[str, str]]:
        """Parse RRULE and return a dict of rule components"""
        if not rrule_line.startswith("RRULE:"):
            return None

        rrule_str = rrule_line[6:]
        rules: dict[str, str] = {}
        for part in rrule_str.split(";"):
            if "=" in part:
                key, value = part.split("=", 1)
                rules[key] = value
        return rules

    def expand_recurring_event(
        self, event: EventDict, rrule: dict[str, str], max_instances: int = 100
    ) -> list[EventDict]:
        """Generate instances of a recurring event"""
        if not rrule or not event["start"]:
            return [event]

        freq = rrule.get("FREQ")
        count = int(rrule.get("COUNT", max_instances))
        until = rrule.get("UNTIL")
        interval = int(rrule.get("INTERVAL", 1))

        until_dt: Optional[datetime] = None
        if until:
            until_dt = self.parse_datetime(until)

        instances: list[EventDict] = []
        current_start: datetime = event["start"]
        duration: timedelta = (
            event["end"] - event["start"] if event["end"] else timedelta(hours=1)
        )

        for i in range(count):
            if until_dt and current_start > until_dt:
                break

            instance = event.copy()
            instance["start"] = current_start
            instance["end"] = current_start + duration
            instances.append(instance)

            if freq == "DAILY":
                current_start += timedelta(days=interval)
            elif freq == "WEEKLY":
                current_start += timedelta(weeks=interval)
            elif freq == "MONTHLY":
                month = current_start.month + interval
                year = current_start.year + (month - 1) // 12
                month = ((month - 1) % 12) + 1
                try:
                    current_start = current_start.replace(year=year, month=month)
                except ValueError:
                    import calendar

                    last_day = calendar.monthrange(year, month)[1]
                    current_start = current_start.replace(
                        year=year, month=month, day=last_day
                    )
            elif freq == "YEARLY":
                current_start = current_start.replace(
                    year=current_start.year + interval
                )
            else:
                break

        return instances

    def expand_multiday_events(self) -> None:
        """Expand multi-day events into separate daily events"""
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

    def fetch_from_url(self, url: str) -> str:
        """Fetch iCal content from a URL or from cache"""
        cached = self.cache.get(url)
        if cached:
            return cached

        try:
            req = Request(url, headers={"User-Agent": "iCal-Viewer/1.0"})
            with urlopen(req, timeout=10) as response:
                content = response.read().decode("utf-8")
                self.cache.set(url, content)
                return content
        except HTTPError as e:
            raise Exception(f"HTTP Error {e.code}: {e.reason}")
        except URLError as e:
            raise Exception(f"URL Error: {e.reason}")
        except Exception as e:
            raise Exception(f"Failed to fetch URL: {str(e)}")

    def parse_file(self, source: str) -> None:
        try:
            if source.startswith("http://") or source.startswith("https://"):
                content = self.fetch_from_url(source)
            else:
                with open(source, "r", encoding="utf-8") as f:
                    content = f.read()
        except Exception as e:
            print(f"Error reading {source}: {e}", file=sys.stderr)
            return
        lines = self.unfold_lines(content)
        in_event = False
        event_lines: list[str] = []
        for line in lines:
            if line == "BEGIN:VEVENT":
                in_event, event_lines = True, []
            elif line == "END:VEVENT":
                if event_lines:
                    event = self.parse_event(event_lines)
                    if event["start"]:
                        if event.get("rrule"):
                            instances = self.expand_recurring_event(
                                event, event["rrule"]
                            )
                            self.events.extend(instances)
                        else:
                            self.events.append(event)
                in_event = False
            elif in_event:
                event_lines.append(line)

    def load_sources(self, sources: list[str]) -> None:
        for src in sources:
            self.parse_file(src)
            self.expand_multiday_events()
