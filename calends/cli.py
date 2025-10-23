"""Command-line interface for the calends calendar viewer."""

import sys
import argparse
from datetime import datetime, timedelta, timezone
from typing import Optional
from .colors import Colors
from .calendar_manager import CalendarManager
from .view import WeeklyView
from .config import find_default_config, load_config, parse_timezone


def main() -> None:
    """Main entry point for the calends CLI application."""
    parser = argparse.ArgumentParser(
        prog="calends",
        description="Display your iCal calendar events in a beautiful weekly terminal view",
        epilog="""
Examples:
  %(prog)s calendar.ics                          # View local calendar file
  %(prog)s https://example.com/calendar.ics      # View calendar from URL
  %(prog)s -c config.json                        # Use config file (calendars.json or calends.json auto-detected)
  %(prog)s -d 2025-12-25                         # View specific week (auto-adjusts to Monday)
  %(prog)s -tz UTC calendar.ics                  # View in specific timezone
  %(prog)s -tz +05:30 calendar.ics               # View with UTC offset

Config file format (calendars.json or calends.json):
  {
    "calendars": ["https://example.com/cal1.ics", "path/to/cal2.ics"],
    "timezone": "UTC",
    "cache_expiration": 3600
  }

For more information, visit: https://github.com/anthropics/claude-code
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "sources",
        nargs="*",
        metavar="SOURCE",
        help="iCal calendar sources (.ics files or URLs). Can be local paths or HTTP(S) URLs.",
    )
    parser.add_argument(
        "-c",
        "--config",
        metavar="FILE",
        help="Path to JSON configuration file containing calendar sources and settings. "
        "If not specified, looks for 'calendars.json' or 'calends.json' in current directory.",
    )
    parser.add_argument(
        "-d",
        "--date",
        metavar="YYYY-MM-DD",
        help="Start date for the week view (automatically adjusts to Monday). "
        "Default: current week.",
    )
    parser.add_argument(
        "-tz",
        "--timezone",
        metavar="TZ",
        help="Timezone for displaying events. Supports: 'UTC', 'LOCAL', or offset format like '+05:30' or '-08:00'. "
        "Default: local timezone.",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable colored output (useful for non-interactive terminals or piping).",
    )
    args = parser.parse_args()

    if args.no_color or not sys.stdout.isatty():
        Colors.disable()

    start: Optional[datetime] = None
    if args.date:
        try:
            start = datetime.strptime(args.date, "%Y-%m-%d")
            start -= timedelta(days=start.weekday())
            start = start.replace(hour=0, minute=0)
        except ValueError:
            print("Invalid date format. Use YYYY-MM-DD", file=sys.stderr)
            sys.exit(1)

    sources: list[str] = []
    tz_str: Optional[str] = None
    cache_exp: int = 60
    if args.config:
        s, tz_str, cache_exp = load_config(args.config)
        sources += s
    elif not args.sources:
        default = find_default_config()
        if default:
            print(f"Using config file: {default}")
            s, tz_str, cache_exp = load_config(default)
            sources += s
    if args.sources:
        sources += args.sources

    if not sources:
        print("No calendar sources provided.", file=sys.stderr)
        sys.exit(1)

    tz_str = args.timezone or tz_str
    tz: Optional[timezone] = parse_timezone(tz_str) if tz_str else None
    if tz_str and tz:
        print(f"Using timezone: {tz_str}")

    manager: CalendarManager = CalendarManager(target_timezone=tz, cache_expiration=cache_exp)
    manager.load_sources(sources)

    if manager.count_events() == 0:
        print("No events found.", file=sys.stderr)
        sys.exit(1)

    view: WeeklyView = WeeklyView(manager.get_all_events(), start, tz)
    view.display()
