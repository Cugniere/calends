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
  %(prog)s -i calendar.ics                       # Interactive mode (navigate with arrow keys)

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
    parser.add_argument(
        "--no-progress",
        action="store_true",
        help="Disable progress indicators during calendar loading.",
    )
    parser.add_argument(
        "-i",
        "--interactive",
        action="store_true",
        help="Enable interactive mode for navigating between weeks.",
    )
    parser.add_argument(
        "--clear-cache",
        action="store_true",
        help="Clear the calendar cache and exit.",
    )
    parser.add_argument(
        "--cache-info",
        action="store_true",
        help="Display cache information and exit.",
    )
    args = parser.parse_args()

    if args.no_color or not sys.stdout.isatty():
        Colors.disable()

    # Handle cache management commands
    if args.clear_cache:
        from .cache import Cache

        cache = Cache()
        cache.clear()
        print(f"{Colors.GREEN}✓{Colors.RESET} Cache cleared successfully")
        print(f"  Cache file: {cache.path}")
        sys.exit(0)

    if args.cache_info:
        from .cache import Cache

        cache = Cache()
        stats = cache.get_stats()
        print(f"{Colors.BOLD}Cache Information:{Colors.RESET}")
        print(f"  Location: {stats['cache_path']}")
        print(
            f"  Exists: {Colors.GREEN if stats['cache_file_exists'] else Colors.RED}{stats['cache_file_exists']}{Colors.RESET}"
        )
        print(f"  Total entries: {stats['total_entries']}")
        print(f"  Valid entries: {Colors.CYAN}{stats['valid_entries']}{Colors.RESET}")
        if stats["total_entries"] > stats["valid_entries"]:
            expired = stats["total_entries"] - stats["valid_entries"]
            print(f"  Expired entries: {Colors.DIM}{expired}{Colors.RESET}")
        sys.exit(0)

    start: Optional[datetime] = None
    if args.date:
        try:
            start = datetime.strptime(args.date, "%Y-%m-%d")
            start -= timedelta(days=start.weekday())
            start = start.replace(hour=0, minute=0)
        except ValueError as e:
            print(
                f"Error: Invalid date format '{args.date}'. Use YYYY-MM-DD (e.g., 2025-01-15)",
                file=sys.stderr,
            )
            sys.exit(1)
        except Exception as e:
            print(f"Error: Failed to parse date: {e}", file=sys.stderr)
            sys.exit(1)

    sources: list[str] = []
    tz_str: Optional[str] = None
    cache_exp: int = 60
    if args.config:
        try:
            s, tz_str, cache_exp = load_config(args.config)
            sources += s
        except FileNotFoundError:
            print(f"Error: Config file not found: {args.config}", file=sys.stderr)
            sys.exit(1)
        except PermissionError:
            print(
                f"Error: Permission denied reading config file: {args.config}",
                file=sys.stderr,
            )
            sys.exit(1)
        except ValueError as e:
            print(f"Error: Invalid config file: {e}", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"Error: Failed to load config file: {e}", file=sys.stderr)
            sys.exit(1)
    elif not args.sources:
        default = find_default_config()
        if default:
            print(f"Using config file: {default}")
            try:
                s, tz_str, cache_exp = load_config(default)
                sources += s
            except Exception as e:
                print(
                    f"Warning: Failed to load config file {default}: {e}",
                    file=sys.stderr,
                )

    if args.sources:
        sources += args.sources

    if not sources:
        print("Error: No calendar sources provided.", file=sys.stderr)
        print("Use --help for usage information.", file=sys.stderr)
        sys.exit(1)

    tz_str = args.timezone or tz_str
    tz: Optional[timezone] = None
    if tz_str:
        try:
            tz = parse_timezone(tz_str)
            if tz:
                print(f"Using timezone: {tz_str}")
            else:
                print(
                    f"Warning: Could not parse timezone '{tz_str}', using local time",
                    file=sys.stderr,
                )
        except Exception as e:
            print(
                f"Warning: Invalid timezone '{tz_str}': {e}. Using local time.",
                file=sys.stderr,
            )

    show_progress = not args.no_progress and sys.stderr.isatty()

    try:
        manager: CalendarManager = CalendarManager(
            target_timezone=tz,
            cache_expiration=cache_exp,
            show_progress=show_progress,
        )
        manager.load_sources(sources)
    except Exception as e:
        print(f"Error: Failed to load calendar sources: {e}", file=sys.stderr)
        sys.exit(1)

    if manager.count_events() == 0:
        print("No events found in the calendar(s).", file=sys.stderr)
        sys.exit(1)

    try:
        # Create refresh callback for interactive mode
        refresh_callback = manager.reload_sources if args.interactive else None

        view: WeeklyView = WeeklyView(
            manager.get_all_events(), start, tz, refresh_callback=refresh_callback
        )

        if args.interactive:
            view.display_interactive()
        else:
            view.display()
    except Exception as e:
        print(f"Error: Failed to display calendar: {e}", file=sys.stderr)
        sys.exit(1)
