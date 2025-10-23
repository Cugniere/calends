from datetime import datetime, timedelta, timezone
from collections import defaultdict
from .colors import Colors

class WeeklyView:
    """Display events in a weekly terminal view."""

    def __init__(self, events, start_date=None, target_timezone=None):
        self.events = events
        self.target_timezone = target_timezone or timezone.utc
        self.start_date = start_date or self.get_monday()
        if self.start_date.tzinfo is None:
            self.start_date = self.start_date.replace(tzinfo=self.target_timezone)
        self.end_date = self.start_date + timedelta(days=7)

    def get_monday(self):
        today = datetime.now()
        monday = today - timedelta(days=today.weekday())
        return monday.replace(hour=0, minute=0, second=0, microsecond=0)

    def filter_events_for_week(self):
        week_events = defaultdict(list)
        for e in self.events:
            if e['start'] and self.start_date <= e['start'] < self.end_date:
                week_events[e['start'].date()].append(e)
        for day in week_events:
            week_events[day].sort(key=lambda ev: ev['start'])
        return week_events

    def format_time(self, dt): return dt.strftime('%H:%M')
    def truncate(self, text, n): return text if len(text)<=n else text[:n-3]+'...'

    def display(self):
        week = self.filter_events_for_week()
        now = datetime.now(self.target_timezone)
        week_number = now.isocalendar().week
        print(f"\n{Colors.BOLD}{'='*80}{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.CYAN}Week {week_number}, {self.start_date.strftime('%B %Y')}{Colors.RESET}")
        print(f"{Colors.BOLD}{'='*80}{Colors.RESET}\n")
        days = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']
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
                    start, end = self.format_time(e['start']), self.format_time(e['end'])
                    time_range = f"{start} - {end}" if start != end else "All day"
                    color = Colors.DIM if e['end'] < now else Colors.BLUE
                    print(f"{color}  {time_range:<15}{Colors.RESET if not is_past else ''}{e['summary']}{Colors.RESET}")
                    if e['location']:
                        print(f"{Colors.CYAN}                   ⚲ {self.truncate(e['location'],60)}{Colors.RESET}")
            else:
                print(f"{Colors.DIM}  No events{Colors.RESET}")
        total = sum(len(v) for v in week.values())
        print(f"\n{Colors.BOLD}{'='*80}{Colors.RESET}")
        print(f"{Colors.BOLD}Total events: {total}{Colors.RESET}")
