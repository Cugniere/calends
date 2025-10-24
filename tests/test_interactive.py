import pytest
from datetime import datetime, timezone, timedelta
from calends.view import WeeklyView


class TestWeekNavigation:
    def test_set_week(self):
        events = [
            {
                "start": datetime(2025, 10, 23, 14, 0, 0, tzinfo=timezone.utc),
                "end": datetime(2025, 10, 23, 15, 0, 0, tzinfo=timezone.utc),
                "summary": "Test Event",
                "location": "",
                "description": "",
            }
        ]
        view = WeeklyView(events, target_timezone=timezone.utc)

        new_date = datetime(2025, 10, 25, 12, 0, 0, tzinfo=timezone.utc)
        view.set_week(new_date)

        assert view.start_date.weekday() == 0
        assert view.start_date.day == 20

    def test_next_week(self):
        events = []
        view = WeeklyView(events, target_timezone=timezone.utc)
        initial_start = view.start_date

        view.next_week()

        assert (view.start_date - initial_start).days == 7

    def test_previous_week(self):
        events = []
        view = WeeklyView(events, target_timezone=timezone.utc)
        initial_start = view.start_date

        view.previous_week()

        assert (initial_start - view.start_date).days == 7

    def test_go_to_today(self):
        events = []
        view = WeeklyView(events, target_timezone=timezone.utc)

        view.set_week(datetime(2020, 1, 1, tzinfo=timezone.utc))
        view.go_to_today()

        now = datetime.now(timezone.utc)
        monday = now - timedelta(days=now.weekday())

        assert view.start_date.date() == monday.date()

    def test_week_navigation_preserves_timezone(self):
        events = []
        tz = timezone(timedelta(hours=5, minutes=30))
        view = WeeklyView(events, target_timezone=tz)

        view.next_week()
        assert view.start_date.tzinfo == tz

        view.previous_week()
        assert view.start_date.tzinfo == tz

    def test_set_week_adjusts_to_monday(self):
        events = []
        view = WeeklyView(events, target_timezone=timezone.utc)

        friday = datetime(2025, 10, 24, tzinfo=timezone.utc)
        view.set_week(friday)

        assert view.start_date.weekday() == 0
        assert view.start_date.day == 20

    def test_week_number_updates_correctly(self):
        events = []
        view = WeeklyView(events, target_timezone=timezone.utc)

        view.set_week(datetime(2025, 10, 20, tzinfo=timezone.utc))
        week1 = view.start_date.isocalendar().week
        assert week1 == 43

        view.next_week()
        week2 = view.start_date.isocalendar().week
        assert week2 == 44

        view.previous_week()
        view.previous_week()
        week3 = view.start_date.isocalendar().week
        assert week3 == 42

        view.set_week(datetime(2025, 1, 1, tzinfo=timezone.utc))
        week_jan = view.start_date.isocalendar().week
        assert week_jan == 1
