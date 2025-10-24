import sys
from datetime import datetime, timedelta, timezone, date
from collections import defaultdict
from typing import Optional, Any
from .colors import Colors
from .interactive import KeyboardInput

EventDict = dict[str, Any]


class WeeklyView:
    """Display events in a weekly terminal view."""

    def __init__(
        self,
        events: list[EventDict],
        start_date: Optional[datetime] = None,
        target_timezone: Optional[timezone] = None,
    ) -> None:
        self.events: list[EventDict] = events
        self.target_timezone: timezone = target_timezone or timezone.utc
        self.start_date: datetime = start_date or self.get_monday()
        if self.start_date.tzinfo is None:
            self.start_date = self.start_date.replace(tzinfo=self.target_timezone)
        self.end_date: datetime = self.start_date + timedelta(days=7)

    def get_monday(self) -> datetime:
        """
        Get the Monday of the current week in the target timezone.

        Returns:
            Datetime object for Monday at midnight
        """
        today = datetime.now(self.target_timezone)
        monday = today - timedelta(days=today.weekday())
        return monday.replace(hour=0, minute=0, second=0, microsecond=0)

    def _ensure_timezone(self, dt: Optional[datetime]) -> Optional[datetime]:
        """
        Ensure a datetime has timezone info.

        Args:
            dt: Datetime to check

        Returns:
            Datetime with timezone info, or None if input is None
        """
        if dt is None:
            return None
        if dt.tzinfo is None:
            return dt.replace(tzinfo=self.target_timezone)
        return dt

    def filter_events_for_week(self) -> defaultdict[date, list[EventDict]]:
        """
        Filter events that fall within the current week.

        Returns:
            Dictionary mapping dates to lists of events for that day
        """
        week_events: defaultdict[date, list[EventDict]] = defaultdict(list)
        for e in self.events:
            if not e["start"]:
                continue

            # Ensure event start time has timezone info for comparison
            event_start = self._ensure_timezone(e["start"])

            if self.start_date <= event_start < self.end_date:
                week_events[event_start.date()].append(e)

        # Sort events by start time, ensuring all have timezone info
        for day in week_events:
            week_events[day].sort(key=lambda ev: self._ensure_timezone(ev["start"]))
        return week_events

    def format_time(self, dt: datetime) -> str:
        return dt.strftime("%H:%M")

    def truncate(self, text: str, n: int) -> str:
        return text if len(text) <= n else text[: n - 3] + "..."

    def display(self) -> None:
        week = self.filter_events_for_week()
        now = datetime.now(self.target_timezone)
        week_number = self.start_date.isocalendar().week
        print(f"\n{Colors.BOLD}{'='*80}{Colors.RESET}")
        print(
            f"{Colors.BOLD}{Colors.CYAN}Week {week_number}, {self.start_date.strftime('%B %Y')}{Colors.RESET}"
        )
        print(f"{Colors.BOLD}{'='*80}{Colors.RESET}\n")
        days = [
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
            "Sunday",
        ]
        for i, dname in enumerate(days):
            current = self.start_date + timedelta(days=i)
            key = current.date()
            is_today = key == now.date()
            is_past = key < now.date()
            day_color = Colors.DIM if is_past else Colors.WHITE
            header = f"{Colors.GREEN if is_today else day_color}{dname}, {current.strftime('%b %d')}{Colors.RESET}"
            print(f"\n{Colors.BOLD}{header}{Colors.RESET}")
            print(f"{Colors.DIM}{'-'*80}{Colors.RESET}")
            if key in week:
                for e in week[key]:
                    start, end = self.format_time(e["start"]), self.format_time(
                        e["end"]
                    )
                    time_range = f"{start} - {end}" if start != end else "All day"

                    # Check if event is currently ongoing (ensure timezone-aware comparison)
                    event_start = self._ensure_timezone(e["start"])
                    event_end = self._ensure_timezone(e["end"])
                    is_ongoing = event_start <= now < event_end

                    # Set background and text color
                    if is_ongoing:
                        bg_color = Colors.BG_RED
                        text_color = Colors.BOLD
                        # Build the line and pad to 80 chars
                        line = f"  {time_range:<15}{e['summary']}"
                        line = line.ljust(80)
                        print(f"{bg_color}{text_color}{line}{Colors.RESET}")
                        if e["location"]:
                            loc_line = f"                   ⚲ {self.truncate(e['location'],60)}"
                            loc_line = loc_line.ljust(80)
                            print(f"{bg_color}{Colors.CYAN}{loc_line}{Colors.RESET}")
                    elif event_end < now:
                        print(
                            f"{Colors.DIM}  {time_range:<15}{Colors.RESET}{e['summary']}{Colors.RESET}"
                        )
                        if e["location"]:
                            print(
                                f"{Colors.CYAN}                   ⚲ {self.truncate(e['location'],60)}{Colors.RESET}"
                            )
                    else:
                        print(
                            f"{Colors.BLUE}  {time_range:<15}{Colors.RESET}{e['summary']}{Colors.RESET}"
                        )
                        if e["location"]:
                            print(
                                f"{Colors.CYAN}                   ⚲ {self.truncate(e['location'],60)}{Colors.RESET}"
                            )
            else:
                print(f"{Colors.DIM}  No events{Colors.RESET}")
        total = sum(len(v) for v in week.values())
        print(f"\n{Colors.BOLD}{'='*80}{Colors.RESET}")
        print(f"{Colors.BOLD}Total events: {total}{Colors.RESET}")

    def set_week(self, start_date: datetime) -> None:
        """
        Set the week to display.

        Args:
            start_date: Start date for the week (will be adjusted to Monday)
        """
        monday = start_date - timedelta(days=start_date.weekday())
        self.start_date = monday.replace(hour=0, minute=0, second=0, microsecond=0)
        if self.start_date.tzinfo is None:
            self.start_date = self.start_date.replace(tzinfo=self.target_timezone)
        self.end_date = self.start_date + timedelta(days=7)

    def next_week(self) -> None:
        """Move to the next week."""
        self.set_week(self.start_date + timedelta(days=7))

    def previous_week(self) -> None:
        """Move to the previous week."""
        self.set_week(self.start_date - timedelta(days=7))

    def go_to_today(self) -> None:
        """Go to the current week."""
        self.set_week(datetime.now(self.target_timezone))

    def display_interactive(self) -> None:
        """
        Display the calendar in interactive mode with navigation.

        Allows the user to navigate between weeks using keyboard controls.
        """
        if not sys.stdout.isatty():
            print("Error: Interactive mode requires a TTY", file=sys.stderr)
            self.display()
            return

        kb = KeyboardInput()
        running = True

        while running:
            kb.clear_screen()
            self.display()
            print(f"\n{Colors.DIM}[n]ext  [p]revious  [t]oday  [j]ump  [h]elp  [q]uit{Colors.RESET}", flush=True)

            key = kb.get_key()

            if key in ['q', 'Q', 'ESC', 'CTRL_C', 'CTRL_D']:
                running = False
            elif key in ['n', 'N', 'RIGHT', ' ']:
                self.next_week()
            elif key in ['p', 'P', 'LEFT']:
                self.previous_week()
            elif key in ['t', 'T']:
                self.go_to_today()
            elif key in ['j', 'J']:
                self._jump_to_date(kb)
            elif key in ['h', 'H', '?']:
                kb.show_help()
                kb.get_key()

        kb.clear_screen()

    def _jump_to_date(self, kb: KeyboardInput) -> None:
        """
        Prompt user to jump to a specific date.

        Args:
            kb: KeyboardInput instance
        """
        print(f"\n{Colors.CYAN}Jump to date (YYYY-MM-DD): {Colors.RESET}", end='', flush=True)

        import termios
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
            date_str = input().strip()

            try:
                target_date = datetime.strptime(date_str, "%Y-%m-%d")
                target_date = target_date.replace(tzinfo=self.target_timezone)
                self.set_week(target_date)
            except ValueError:
                print(f"{Colors.RED}Invalid date format. Press any key to continue...{Colors.RESET}", flush=True)
                kb.get_key()
        except (KeyboardInterrupt, EOFError):
            pass
