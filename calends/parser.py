import sys
import re
from datetime import datetime, timedelta, timezone
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from .cache import Cache

class ICalParser:
    """Parse iCal files from url"""

    def __init__(self, target_timezone=None, cache_expiration=60):
        self.events = []
        self.target_timezone = target_timezone
        self.cache = Cache(expiration_seconds=cache_expiration)

    def unfold_lines(self, content: str):
        """Unfold lines that are split with CRLF + space/tab."""
        lines = content.replace('\r\n', '\n').replace('\r', '\n').split('\n')
        unfolded, current = [], ''
        for line in lines:
            if line and line[0] in (' ', '\t'):
                current += line[1:]
            else:
                if current:
                    unfolded.append(current)
                current = line
        if current:
            unfolded.append(current)
        return unfolded

    def parse_datetime(self, dt_string: str):
        if not dt_string:
            return None
        if ';' in dt_string or ':' in dt_string:
            dt_string = dt_string.split(':')[-1]
        formats = [
            ('%Y%m%dT%H%M%SZ', True),
            ('%Y%m%dT%H%M%S', False),
            ('%Y%m%d', False),
        ]
        dt, is_utc = None, False
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

    def parse_event(self, lines):
        event = {'summary': 'Untitled Event', 'start': None, 'end': None,
                 'location': '', 'description': ''}
        for line in lines:
            if line.startswith('SUMMARY:'):
                event['summary'] = line[8:]
            elif line.startswith('DTSTART'):
                event['start'] = self.parse_datetime(line)
            elif line.startswith('DTEND'):
                event['end'] = self.parse_datetime(line)
            elif line.startswith('LOCATION:'):
                event['location'] = line[9:]
            elif line.startswith('DESCRIPTION:'):
                event['description'] = line[12:]
        
        # If no timezone is specified, assume that it is from the current timezone
        if event['start'] and not event['start'].tzinfo:
            event['start'] = event['start'].replace(tzinfo=self.target_timezone)
        if event['end'] and not event['end'].tzinfo:
            event['end'] = event['end'].replace(tzinfo=self.target_timezone)

        if event['start'] and not event['end']:
            event['end'] = event['start'] + timedelta(hours=1)

        return event

    def expand_multiday_events(self):
        """Expand multi-day events into separate daily events"""
        expanded = []
        for event in self.events:
            if not event['start'] or not event['end']:
                expanded.append(event)
                continue
            
            # Get date-only parts for comparison
            start_date = event['start'].date()
            end_date = event['end'].date()
            
            # If same day, keep as-is
            if start_date == end_date:
                expanded.append(event)
                continue
            
            # Create an event for each day (end_date is exclusive)
            current_date = start_date
            while current_date < end_date:  # Changed from <= to 
                day_event = event.copy()
                
                # First day: use original start time
                if current_date == start_date:
                    day_event['start'] = event['start']
                    # End at midnight of next day
                    next_midnight = datetime.combine(current_date + timedelta(days=1), 
                                                    datetime.min.time())
                    if event['start'].tzinfo:
                        next_midnight = next_midnight.replace(tzinfo=event['start'].tzinfo)
                    day_event['end'] = next_midnight
                # Last day: start at midnight, use original end time
                elif current_date == end_date - timedelta(days=1):
                    day_start = datetime.combine(current_date, datetime.min.time())
                    if event['start'].tzinfo:
                        day_start = day_start.replace(tzinfo=event['start'].tzinfo)
                    day_event['start'] = day_start
                    day_event['end'] = event['end']
                # Middle days: full day
                else:
                    day_start = datetime.combine(current_date, datetime.min.time())
                    day_end = datetime.combine(current_date + timedelta(days=1), datetime.min.time())
                    if event['start'].tzinfo:
                        day_start = day_start.replace(tzinfo=event['start'].tzinfo)
                        day_end = day_end.replace(tzinfo=event['start'].tzinfo)
                    day_event['start'] = day_start
                    day_event['end'] = day_end
                
                expanded.append(day_event)
                current_date += timedelta(days=1)
        
        self.events = expanded

    def fetch_from_url(self, url: str) -> str:
        """Fetch iCal content from a URL or from cache"""
        cached = self.cache.get(url)
        if cached:
            return cached

        try:
            req = Request(url, headers={'User-Agent': 'iCal-Viewer/1.0'})
            with urlopen(req, timeout=10) as response:
                content = response.read().decode('utf-8')
                self.cache.set(url, content)
                return content
        except HTTPError as e:
            raise Exception(f"HTTP Error {e.code}: {e.reason}")
        except URLError as e:
            raise Exception(f"URL Error: {e.reason}")
        except Exception as e:
            raise Exception(f"Failed to fetch URL: {str(e)}")

    def parse_file(self, source: str):
        try:
            if source.startswith('http://') or source.startswith('https://'):
                content = self.fetch_from_url(source)
            else:
                with open(source, 'r', encoding='utf-8') as f:
                    content = f.read()
        except Exception as e:
            print(f"Error reading {source}: {e}", file=sys.stderr)
            return
        lines = self.unfold_lines(content)
        in_event, event_lines = False, []
        for line in lines:
            if line == 'BEGIN:VEVENT':
                in_event, event_lines = True, []
            elif line == 'END:VEVENT':
                if event_lines:
                    event = self.parse_event(event_lines)
                    if event['start']:
                        self.events.append(event)
                in_event = False
            elif in_event:
                event_lines.append(line)

    def load_sources(self, sources):
        for src in sources:
            self.parse_file(src)
            self.expand_multiday_events()
