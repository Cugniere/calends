import sys
import threading
import time
from datetime import datetime, timedelta, timezone, date
from collections import defaultdict
from typing import Optional, Any, Callable
from .colors import Colors
from .interactive import KeyboardInput
from .constants import DEFAULT_AUTO_REFRESH_INTERVAL

EventDict = dict[str, Any]


class WeeklyView:
    """Display events in a weekly terminal view."""

    def __init__(
        self,
        events: list[EventDict],
        start_date: Optional[datetime] = None,
        target_timezone: Optional[timezone] = None,
        refresh_callback: Optional[Callable[[], list[EventDict]]] = None,
        auto_refresh_interval: int = DEFAULT_AUTO_REFRESH_INTERVAL,
        calendar_manager: Optional[Any] = None,
    ) -> None:
        self.events: list[EventDict] = events
        self.target_timezone: timezone = target_timezone or timezone.utc
        self.start_date: datetime = start_date or self.get_monday()
        if self.start_date.tzinfo is None:
            self.start_date = self.start_date.replace(tzinfo=self.target_timezone)
        self.end_date: datetime = self.start_date + timedelta(days=7)
        self.refresh_callback: Optional[Callable[[], list[EventDict]]] = (
            refresh_callback
        )
        self.auto_refresh_interval: int = auto_refresh_interval
        self.calendar_manager: Optional[Any] = calendar_manager
        self._refresh_thread: Optional[threading.Thread] = None
        self._stop_refresh: threading.Event = threading.Event()
        self._needs_redraw: threading.Event = threading.Event()
        self._selected_event_index: int = 0

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

    def _get_all_week_events(self) -> list[EventDict]:
        """
        Get all events for the current week in chronological order.

        Returns:
            List of events sorted by start time
        """
        week = self.filter_events_for_week()
        all_events = []
        # Get days in order from Monday to Sunday
        for i in range(7):
            day_date = (self.start_date + timedelta(days=i)).date()
            if day_date in week:
                all_events.extend(week[day_date])
        return all_events

    def _display_event_details(self, event: EventDict) -> None:
        """
        Display detailed information about an event.

        Args:
            event: Event dictionary to display
        """
        import re
        import textwrap

        width = 76

        def wrap_field(label: str, value: str) -> list[str]:
            """Wrap a field to fit within the box width."""
            if not value:
                return []

            # Colorize the label
            colored_label = f"{Colors.GREEN}{label}{Colors.RESET}"

            first_line = f"{label} {value}"
            if len(first_line) <= width:
                return [f"{colored_label} {value}"]

            # Need to wrap
            indent = " " * (len(label) + 1)
            available_width = width - len(label) - 1
            wrapped = textwrap.wrap(value, width=available_width)

            result = [f"{colored_label} {wrapped[0]}"]
            for line in wrapped[1:]:
                result.append(f"{indent}{line}")
            return result

        lines = []

        # Title
        lines.extend(wrap_field("Title:", event["summary"]))

        # Calendar name
        if event.get("calendar_name"):
            lines.extend(wrap_field("Calendar:", event["calendar_name"]))

        # Time
        start_time = event["start"].strftime("%A, %B %d, %Y at %H:%M")
        end_time = event["end"].strftime("%H:%M")
        if event["start"].date() != event["end"].date():
            end_time = event["end"].strftime("%A, %B %d, %Y at %H:%M")
        lines.extend(wrap_field("Time:", f"{start_time} - {end_time}"))

        # Location
        if event.get("location"):
            lines.extend(wrap_field("Location:", event["location"]))

        # Attendees
        if event.get("attendees") and len(event["attendees"]) > 0:
            attendees_str = ", ".join(event["attendees"])
            lines.extend(wrap_field("Attendees:", attendees_str))

        # Description
        if event.get("description"):
            desc = event["description"].strip()
            if desc:
                desc = re.sub(r"<[^>]+>", "", desc)
                desc = desc.strip()
                if desc:
                    lines.extend(wrap_field("Description:", desc))

        # Top border - total width is 80 (76 content + 2 spaces + 2 borders)
        title = " Event Details "
        border_width = width + 2  # 78 chars between borders
        padding = (border_width - len(title)) // 2
        top = f"┌{'─' * padding}{title}{'─' * (border_width - padding - len(title))}┐"
        print(f"\n{Colors.BOLD}{top}{Colors.RESET}")

        # Content lines
        ansi_escape = re.compile(r"\x1b\[[0-9;]*m")
        for line in lines:
            # Calculate visual length without ANSI codes
            visual_len = len(ansi_escape.sub("", line))
            padding_needed = width - visual_len
            padded = line + (" " * padding_needed)
            print(f"{Colors.BOLD}│{Colors.RESET} {padded} {Colors.BOLD}│{Colors.RESET}")

        # Bottom border
        bottom = f"└{'─' * border_width}┘"
        print(f"{Colors.BOLD}{bottom}{Colors.RESET}")

    def display(self, selected_event_index: Optional[int] = None) -> None:
        week = self.filter_events_for_week()
        now = datetime.now(self.target_timezone)
        week_number = self.start_date.isocalendar().week
        week_title = f"Week {week_number}, {self.start_date.strftime('%B %Y')}"
        centered_title = week_title.center(80)
        print(f"\n{Colors.BOLD}{'═'*80}{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.CYAN}{centered_title}{Colors.RESET}")
        print(f"{Colors.BOLD}{'═'*80}{Colors.RESET}\n")
        days = [
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
            "Sunday",
        ]

        # Track global event index for selection
        event_counter = 0

        for i, dname in enumerate(days):
            current = self.start_date + timedelta(days=i)
            key = current.date()
            is_today = key == now.date()
            is_past = key < now.date()
            day_color = Colors.DIM if is_past else Colors.WHITE
            header = f"{Colors.GREEN if is_today else day_color}{dname}, {current.strftime('%b %d')}{Colors.RESET}"
            print(f"\n{Colors.BOLD}{header}{Colors.RESET}")
            print(f"{Colors.DIM}{'─'*80}{Colors.RESET}")
            if key in week:
                for e in week[key]:
                    is_selected = (
                        selected_event_index is not None
                        and event_counter == selected_event_index
                    )
                    selection_marker = "▶ " if is_selected else "  "
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
                        line = f"{selection_marker}{time_range:<15}{e['summary']}"
                        line = line.ljust(80)
                        print(f"{bg_color}{text_color}{line}{Colors.RESET}")
                        if e["location"]:
                            loc_line = f"                   ⚲ {self.truncate(e['location'],60)}"
                            loc_line = loc_line.ljust(80)
                            print(f"{bg_color}{Colors.CYAN}{loc_line}{Colors.RESET}")
                    elif event_end < now:
                        print(
                            f"{Colors.DIM}{selection_marker}{time_range:<15}{Colors.RESET}{e['summary']}{Colors.RESET}"
                        )
                        if e["location"]:
                            print(
                                f"{Colors.CYAN}                   ⚲ {self.truncate(e['location'],60)}{Colors.RESET}"
                            )
                    else:
                        print(
                            f"{Colors.BLUE}{selection_marker}{time_range:<15}{Colors.RESET}{e['summary']}{Colors.RESET}"
                        )
                        if e["location"]:
                            print(
                                f"{Colors.CYAN}                   ⚲ {self.truncate(e['location'],60)}{Colors.RESET}"
                            )

                    event_counter += 1
            else:
                print(f"{Colors.DIM}  No events{Colors.RESET}")
        total = sum(len(v) for v in week.values())
        total_text = f"Total events: {total}"
        centered_total = total_text.center(80)
        print(f"\n{Colors.BOLD}{'═'*80}{Colors.RESET}")
        print(f"{Colors.BOLD}{centered_total}{Colors.RESET}")

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

    def refresh_events(self, silent: bool = False) -> bool:
        """
        Refresh calendar events by calling the refresh callback.

        Args:
            silent: If True, suppress output messages

        Returns:
            True if refresh was successful, False otherwise
        """
        if not self.refresh_callback:
            return False

        try:
            # Temporarily disable progress output for silent refresh
            original_show_progress = None
            if silent and self.calendar_manager:
                original_show_progress = self.calendar_manager.show_progress
                self.calendar_manager.show_progress = False
                # Also disable fetcher progress
                self.calendar_manager.fetcher.show_progress = False

            if not silent:
                print(
                    f"\n{Colors.CYAN}Refreshing calendar data...{Colors.RESET}",
                    flush=True,
                )
            new_events = self.refresh_callback()
            self.events = new_events
            if not silent:
                print(
                    f"{Colors.GREEN}✓{Colors.RESET} Loaded {len(new_events)} events",
                    flush=True,
                )
                time.sleep(0.5)
            return True
        except Exception as e:
            if not silent:
                print(f"{Colors.RED}✗{Colors.RESET} Failed to refresh: {e}", flush=True)
                time.sleep(1.5)
            return False
        finally:
            # Restore original progress setting
            if silent and self.calendar_manager and original_show_progress is not None:
                self.calendar_manager.show_progress = original_show_progress
                self.calendar_manager.fetcher.show_progress = original_show_progress

    def _background_refresh(self) -> None:
        """Background thread that periodically refreshes events."""
        while not self._stop_refresh.wait(self.auto_refresh_interval):
            if self.refresh_callback:
                # Perform silent refresh
                success = self.refresh_events(silent=True)
                if success:
                    # Signal that display needs redraw
                    self._needs_redraw.set()

    def _start_background_refresh(self) -> None:
        """Start the background refresh thread if enabled."""
        if self.auto_refresh_interval > 0 and self.refresh_callback:
            self._stop_refresh.clear()
            self._refresh_thread = threading.Thread(
                target=self._background_refresh, daemon=True
            )
            self._refresh_thread.start()

    def _stop_background_refresh(self) -> None:
        """Stop the background refresh thread."""
        if self._refresh_thread and self._refresh_thread.is_alive():
            self._stop_refresh.set()
            self._refresh_thread.join(timeout=1.0)

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

        # Start background refresh if enabled
        self._start_background_refresh()

        try:
            while running:
                # Check if background refresh triggered a redraw
                if self._needs_redraw.is_set():
                    self._needs_redraw.clear()
                    # Reset selection when events refresh
                    self._selected_event_index = 0

                # Get current week events for navigation
                all_events = self._get_all_week_events()
                total_events = len(all_events)

                # Clamp selected index
                if total_events > 0:
                    self._selected_event_index = max(
                        0, min(self._selected_event_index, total_events - 1)
                    )
                else:
                    self._selected_event_index = 0

                kb.clear_screen()
                self.display(self._selected_event_index if total_events > 0 else None)

                # Build status bar based on available features
                status_items = [
                    "[↑↓]select",
                    "[n]ext",
                    "[p]revious",
                    "[t]oday",
                    "[j]ump",
                ]
                if self.refresh_callback:
                    status_items.append("[r]efresh")
                status_items.extend(["[h]elp", "[q]uit"])
                status_bar = "  ".join(status_items)
                centered_bar = status_bar.center(80)
                print(f"\n{Colors.DIM}{centered_bar}{Colors.RESET}", flush=True)

                # Display selected event details
                if total_events > 0 and 0 <= self._selected_event_index < total_events:
                    selected_event = all_events[self._selected_event_index]
                    self._display_event_details(selected_event)

                key = kb.get_key()

                if key in ["q", "Q", "ESC", "CTRL_C", "CTRL_D"]:
                    running = False
                elif key in ["UP"]:
                    if total_events > 0:
                        self._selected_event_index = (
                            self._selected_event_index - 1
                        ) % total_events
                elif key in ["DOWN"]:
                    if total_events > 0:
                        self._selected_event_index = (
                            self._selected_event_index + 1
                        ) % total_events
                elif key in ["n", "N", "RIGHT", " "]:
                    self.next_week()
                    self._selected_event_index = 0
                elif key in ["p", "P", "LEFT"]:
                    self.previous_week()
                    self._selected_event_index = 0
                elif key in ["t", "T"]:
                    self.go_to_today()
                    self._selected_event_index = 0
                elif key in ["j", "J"]:
                    self._jump_to_date(kb)
                    self._selected_event_index = 0
                elif key in ["r", "R"]:
                    self.refresh_events()
                    self._selected_event_index = 0
                elif key in ["h", "H", "?"]:
                    kb.show_help()
                    kb.get_key()
        finally:
            # Always stop background refresh on exit
            self._stop_background_refresh()

        kb.clear_screen()

    def _jump_to_date(self, kb: KeyboardInput) -> None:
        """
        Prompt user to jump to a specific date.

        Args:
            kb: KeyboardInput instance
        """
        print(
            f"\n{Colors.CYAN}Jump to date (YYYY-MM-DD): {Colors.RESET}",
            end="",
            flush=True,
        )

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
                print(
                    f"{Colors.RED}Invalid date format. Press any key to continue...{Colors.RESET}",
                    flush=True,
                )
                kb.get_key()
        except (KeyboardInterrupt, EOFError):
            pass
