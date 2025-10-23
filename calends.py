#!/usr/bin/env python3
"""
Terminal iCal Weekly Viewer
Parses iCal (.ics) files and displays events in a weekly view.
Uses only Python standard library.
"""

import sys
import re
import os
from datetime import datetime, timedelta, timezone
from collections import defaultdict
import argparse
import json
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError


# ANSI color codes
class Colors:
    """ANSI color codes for terminal output."""
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    
    # Regular colors
    GREY = '\033[90m'
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    
    # Light colors for past events
    LIGHT_GREY = '\033[37m'
    
    @staticmethod
    def disable():
        """Disable colors (for piping or when colors not supported)."""
        Colors.RESET = ''
        Colors.BOLD = ''
        Colors.DIM = ''
        Colors.GREY = ''
        Colors.RED = ''
        Colors.GREEN = ''
        Colors.YELLOW = ''
        Colors.BLUE = ''
        Colors.MAGENTA = ''
        Colors.CYAN = ''
        Colors.WHITE = ''
        Colors.LIGHT_GREY = ''


class ICalParser:
    """Parse iCal files without external dependencies."""
    
    def __init__(self, target_timezone=None):
        self.events = []
        self.target_timezone = target_timezone
    
    def unfold_lines(self, content):
        """Unfold lines that are split with CRLF + space/tab."""
        lines = content.replace('\r\n', '\n').replace('\r', '\n').split('\n')
        unfolded = []
        current = ''
        
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
    
    def parse_datetime(self, dt_string):
        """Parse iCal datetime formats and convert to target timezone."""
        if not dt_string:
            return None
        
        # Remove TZID parameter if present
        if ';' in dt_string:
            dt_string = dt_string.split(':')[-1]
        elif ':' in dt_string:
            dt_string = dt_string.split(':')[-1]
        
        # Handle different formats
        formats = [
            ('%Y%m%dT%H%M%SZ', True),      # 20231025T143000Z (UTC)
            ('%Y%m%dT%H%M%S', False),       # 20231025T143000 (local/no timezone)
            ('%Y%m%d', False),              # 20231025 (date only)
        ]
        
        dt = None
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
        
        # If datetime has 'Z' suffix, it's UTC
        if is_utc:
            dt = dt.replace(tzinfo=timezone.utc)
        
        # Convert to target timezone if specified
        if self.target_timezone and dt.tzinfo:
            dt = dt.astimezone(self.target_timezone)
        elif self.target_timezone and not dt.tzinfo:
            # Assume naive datetime is in local time, make it aware then convert
            dt = dt.replace(tzinfo=None)
        
        return dt
    
    def parse_event(self, event_lines):
        """Parse a single VEVENT component."""
        event = {
            'summary': 'Untitled Event',
            'start': None,
            'end': None,
            'location': '',
            'description': ''
        }
        
        for line in event_lines:
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

        # If end time not specified, default to 1 hour after start
        if event['start'] and not event['end']:
            event['end'] = event['start'] + timedelta(hours=1)
        
        return event
    
    def parse_file(self, source):
        """Parse an iCal file from URL or local path."""
        try:
            # Check if source is a URL
            if source.startswith('http://') or source.startswith('https://'):
                content = self.fetch_from_url(source)
            else:
                with open(source, 'r', encoding='utf-8') as f:
                    content = f.read()
        except Exception as e:
            print(f"Error reading {source}: {e}", file=sys.stderr)
            return
        
        lines = self.unfold_lines(content)
        
        in_event = False
        event_lines = []
        
        for line in lines:
            if line == 'BEGIN:VEVENT':
                in_event = True
                event_lines = []
            elif line == 'END:VEVENT':
                if event_lines:
                    event = self.parse_event(event_lines)
                    if event['start']:
                        self.events.append(event)
                in_event = False
            elif in_event:
                event_lines.append(line)
    
    def fetch_from_url(self, url):
        """Fetch iCal content from a URL."""
        try:
            # Create request with a user agent to avoid being blocked
            req = Request(url, headers={'User-Agent': 'iCal-Viewer/1.0'})
            with urlopen(req, timeout=10) as response:
                content = response.read().decode('utf-8')
                return content
        except HTTPError as e:
            raise Exception(f"HTTP Error {e.code}: {e.reason}")
        except URLError as e:
            raise Exception(f"URL Error: {e.reason}")
        except Exception as e:
            raise Exception(f"Failed to fetch URL: {str(e)}")
    
    def load_sources(self, sources):
        """Load multiple iCal files from URLs or local paths."""
        for source in sources:
            self.parse_file(source)


class WeeklyView:
    """Display events in a weekly terminal view."""
    
    def __init__(self, events, start_date=None):
        self.events = events
        # Determine if we need timezone-aware dates
        has_tz_aware = any(e['start'] and e['start'].tzinfo for e in events if e['start'])
        
        if start_date:
            self.start_date = start_date
        else:
            self.start_date = self.get_monday_of_current_week()
        
        # Make start_date timezone-aware if events are timezone-aware
        if has_tz_aware and self.start_date.tzinfo is None:
            self.start_date = self.start_date.replace(tzinfo=timezone.utc)
        
        self.end_date = self.start_date + timedelta(days=7)
    
    def get_monday_of_current_week(self):
        """Get the Monday of the current week."""
        today = datetime.now()
        monday = today - timedelta(days=today.weekday())
        return monday.replace(hour=0, minute=0, second=0, microsecond=0)
    
    def filter_events_for_week(self):
        """Filter events that fall within the current week."""
        week_events = defaultdict(list)
        
        for event in self.events:
            if not event['start']:
                continue
            
            event_start = event['start']
            
            # Ensure both datetimes are comparable (both aware or both naive)
            if event_start.tzinfo and not self.start_date.tzinfo:
                # Convert event to naive
                event_start = event_start.replace(tzinfo=None)
            elif not event_start.tzinfo and self.start_date.tzinfo:
                # Convert event to aware (assume UTC)
                event_start = event_start.replace(tzinfo=timezone.utc)
            
            if event_start >= self.start_date and event_start < self.end_date:
                day_key = event_start.date()
                week_events[day_key].append(event)
        
        # Sort events by time for each day
        for day in week_events:
            week_events[day].sort(key=lambda e: e['start'])
        
        return week_events
    
    def format_time(self, dt):
        """Format time for display."""
        return dt.strftime('%H:%M')
    
    def truncate(self, text, max_len):
        """Truncate text to max length."""
        if len(text) <= max_len:
            return text
        return text[:max_len-3] + '...'
    
    def display(self):
        """Display the weekly view with colors."""
        week_events = self.filter_events_for_week()
        
        # Get current time for comparison (with timezone awareness if needed)
        now = datetime.now()
        if self.start_date.tzinfo:
            now = datetime.now(timezone.utc)
        
        # Print header
        print(f"\n{Colors.BOLD}{'='*80}{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.CYAN}Week of {self.start_date.strftime('%B %d, %Y')}{Colors.RESET}")
        print(f"{Colors.BOLD}{'='*80}{Colors.RESET}\n")
        
        # Display each day
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        
        for i, day_name in enumerate(days):
            current_date = self.start_date + timedelta(days=i)
            day_key = current_date.date()
            
            # Check if this is today
            is_today = day_key == now.date()
            
            # Day header with color
            if is_today:
                print(f"\n{Colors.BOLD}{Colors.GREEN}{day_name}, {current_date.strftime('%B %d')} (Today){Colors.RESET}")
            else:
                print(f"\n{Colors.BOLD}{day_name}, {current_date.strftime('%B %d')}{Colors.RESET}")
            print(f"{Colors.DIM}{'-' * 80}{Colors.RESET}")
            
            if day_key in week_events and week_events[day_key]:
                for event in week_events[day_key]:
                    start_time = self.format_time(event['start'])
                    end_time = self.format_time(event['end'])
                    summary = self.truncate(event['summary'], 50)
                    
                    # Determine if event is in the past
                    is_past = event['end'] < now
                    
                    if is_past:
                        # Past events in light grey
                        print(f"{Colors.LIGHT_GREY}  {start_time} - {end_time}  {summary}{Colors.RESET}")
                        if event['location']:
                            location = self.truncate(event['location'], 60)
                            print(f"{Colors.LIGHT_GREY}                  📍 {location}{Colors.RESET}")
                    else:
                        # Current/future events with colored time
                        print(f"{Colors.BLUE}  {start_time} - {end_time}{Colors.RESET}  {summary}")
                        if event['location']:
                            location = self.truncate(event['location'], 60)
                            print(f"{Colors.CYAN}                  📍 {location}{Colors.RESET}")
            else:
                print(f"{Colors.DIM}  No events{Colors.RESET}")
        
        print(f"\n{Colors.BOLD}{'='*80}{Colors.RESET}\n")
        
        # Summary
        total_events = sum(len(events) for events in week_events.values())
        print(f"{Colors.BOLD}Total events this week: {total_events}{Colors.RESET}")


def find_default_config():
    """Look for calendars.json in current directory."""
    default_names = ['calendars.json', 'calends.json']
    
    for name in default_names:
        if os.path.isfile(name):
            return name
    
    return None


def parse_timezone(tz_string):
    """Parse timezone string to timezone object.
    
    Supports:
    - UTC offset format: +0530, -0800, +00:00, -05:00
    - 'UTC' or 'GMT'
    - 'local' for system local time
    """
    if not tz_string:
        return None
    
    tz_string = tz_string.strip().upper()
    
    # Handle 'local' keyword
    if tz_string == 'LOCAL':
        return None  # Will use system local time
    
    # Handle UTC/GMT
    if tz_string in ('UTC', 'GMT'):
        return timezone.utc
    
    # Handle offset formats: +0530, -0800, +05:30, -08:00
    match = re.match(r'^([+-])(\d{2}):?(\d{2})$', tz_string)
    if match:
        sign = 1 if match.group(1) == '+' else -1
        hours = int(match.group(2))
        minutes = int(match.group(3))
        offset = timedelta(hours=sign * hours, minutes=sign * minutes)
        return timezone(offset)
    
    print(f"Warning: Invalid timezone format '{tz_string}'. Using local time.", file=sys.stderr)
    return None


def load_config(config_path):
    """Load calendar URLs and timezone from JSON config file."""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        if 'calendars' not in config:
            print("Error: Config file missing 'calendars' field", file=sys.stderr)
            return [], None
        
        if not isinstance(config['calendars'], list):
            print("Error: 'calendars' must be a list", file=sys.stderr)
            return [], None
        
        timezone_str = config.get('timezone', None)
        
        return config['calendars'], timezone_str
    
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON config: {e}", file=sys.stderr)
        return [], None
    except FileNotFoundError:
        print(f"Error: Config file not found: {config_path}", file=sys.stderr)
        return [], None
    except Exception as e:
        print(f"Error reading config file: {e}", file=sys.stderr)
        return [], None


def main():
    parser = argparse.ArgumentParser(
        description='Display iCal files in a weekly terminal view'
    )
    parser.add_argument(
        'sources',
        nargs='*',
        help='One or more .ics file URLs or local file paths'
    )
    parser.add_argument(
        '-c', '--config',
        help='JSON config file containing calendar URLs',
        default=None
    )
    parser.add_argument(
        '-d', '--date',
        help='Start date for the week (YYYY-MM-DD). Defaults to current week.',
        default=None
    )
    parser.add_argument(
        '-tz', '--timezone',
        help='Timezone for display (e.g., +0530, -0800, UTC, local)',
        default=None
    )
    parser.add_argument(
        '--no-color',
        action='store_true',
        help='Disable colored output',
        default=False
    )
    
    args = parser.parse_args()
    
    # Disable colors if requested or if output is not a TTY
    if args.no_color or not sys.stdout.isatty():
        Colors.disable()
    
    # Parse start date if provided
    start_date = None
    if args.date:
        try:
            start_date = datetime.strptime(args.date, '%Y-%m-%d')
            # Adjust to Monday of that week
            start_date = start_date - timedelta(days=start_date.weekday())
            start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        except ValueError:
            print(f"Invalid date format: {args.date}. Use YYYY-MM-DD", file=sys.stderr)
            sys.exit(1)
    
    # Collect all sources and timezone
    all_sources = []
    config_timezone = None
    
    # Load from config file if provided
    if args.config:
        config_sources, config_timezone = load_config(args.config)
        all_sources.extend(config_sources)
    # If no config and no sources provided, look for default config
    elif not args.sources:
        default_config = find_default_config()
        if default_config:
            print(f"Using config file: {default_config}")
            config_sources, config_timezone = load_config(default_config)
            all_sources.extend(config_sources)
    
    # Add command line sources
    if args.sources:
        all_sources.extend(args.sources)
    
    # Check if we have any sources
    if not all_sources:
        print("Error: No calendar sources provided.", file=sys.stderr)
        print("Options:", file=sys.stderr)
        print("  - Create a calendars.json file in the current directory", file=sys.stderr)
        print("  - Use -c to specify a config file", file=sys.stderr)
        print("  - Provide URLs/paths as arguments", file=sys.stderr)
        sys.exit(1)
    
    # Determine timezone: command line overrides config file
    timezone_str = args.timezone if args.timezone else config_timezone
    target_tz = parse_timezone(timezone_str) if timezone_str else None
    
    if timezone_str:
        if target_tz:
            print(f"Using timezone: {timezone_str}")
        # Warning already printed by parse_timezone if invalid
    
    # Parse iCal files
    ical_parser = ICalParser(target_timezone=target_tz)
    ical_parser.load_sources(all_sources)
    
    if not ical_parser.events:
        print("No events found in the provided sources.", file=sys.stderr)
        sys.exit(1)
    
    # Display weekly view
    weekly_view = WeeklyView(ical_parser.events, start_date)
    weekly_view.display()


if __name__ == '__main__':
    main()

