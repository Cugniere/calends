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
    parser = argparse.ArgumentParser(description="Terminal iCal Weekly Viewer")
    parser.add_argument("sources", nargs="*", help="One or more .ics URLs or paths")
    parser.add_argument("-c", "--config", help="Path to JSON config file")
    parser.add_argument("-d", "--date", help="Start date (YYYY-MM-DD)")
    parser.add_argument("-tz", "--timezone", help="Timezone (e.g. +0530, UTC, local)")
    parser.add_argument("--no-color", action="store_true", help="Disable colors")
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
