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


class TestRefreshCallback:
    """Test refresh callback functionality."""

    def test_refresh_events_with_callback(self):
        """Test that refresh_events calls the callback and updates events."""
        events = [
            {
                "start": datetime(2025, 10, 23, 14, 0, 0, tzinfo=timezone.utc),
                "end": datetime(2025, 10, 23, 15, 0, 0, tzinfo=timezone.utc),
                "summary": "Old Event",
                "location": "",
                "description": "",
            }
        ]

        new_events = [
            {
                "start": datetime(2025, 10, 24, 14, 0, 0, tzinfo=timezone.utc),
                "end": datetime(2025, 10, 24, 15, 0, 0, tzinfo=timezone.utc),
                "summary": "New Event",
                "location": "",
                "description": "",
            }
        ]

        def mock_callback():
            return new_events

        view = WeeklyView(events, target_timezone=timezone.utc, refresh_callback=mock_callback)

        assert len(view.events) == 1
        assert view.events[0]["summary"] == "Old Event"

        result = view.refresh_events()

        assert result is True
        assert len(view.events) == 1
        assert view.events[0]["summary"] == "New Event"

    def test_refresh_events_without_callback(self):
        """Test that refresh_events returns False when no callback is provided."""
        events = [
            {
                "start": datetime(2025, 10, 23, 14, 0, 0, tzinfo=timezone.utc),
                "end": datetime(2025, 10, 23, 15, 0, 0, tzinfo=timezone.utc),
                "summary": "Test Event",
                "location": "",
                "description": "",
            }
        ]

        view = WeeklyView(events, target_timezone=timezone.utc, refresh_callback=None)

        assert len(view.events) == 1
        result = view.refresh_events()

        assert result is False
        assert len(view.events) == 1

    def test_refresh_events_with_failing_callback(self):
        """Test that refresh_events handles callback failures gracefully."""

        def failing_callback():
            raise Exception("Network error")

        events = [
            {
                "start": datetime(2025, 10, 23, 14, 0, 0, tzinfo=timezone.utc),
                "end": datetime(2025, 10, 23, 15, 0, 0, tzinfo=timezone.utc),
                "summary": "Test Event",
                "location": "",
                "description": "",
            }
        ]

        view = WeeklyView(events, target_timezone=timezone.utc, refresh_callback=failing_callback)

        original_count = len(view.events)
        result = view.refresh_events()

        assert result is False
        assert len(view.events) == original_count

    def test_refresh_events_with_empty_result(self):
        """Test refresh with callback returning empty list."""

        def empty_callback():
            return []

        events = [
            {
                "start": datetime(2025, 10, 23, 14, 0, 0, tzinfo=timezone.utc),
                "end": datetime(2025, 10, 23, 15, 0, 0, tzinfo=timezone.utc),
                "summary": "Test Event",
                "location": "",
                "description": "",
            }
        ]

        view = WeeklyView(events, target_timezone=timezone.utc, refresh_callback=empty_callback)

        result = view.refresh_events()

        assert result is True
        assert len(view.events) == 0


class TestJumpToDateEdgeCases:
    """Test edge cases for date jumping functionality."""

    def test_set_week_with_leap_year_date(self):
        """Test jumping to Feb 29 in a leap year."""
        events = []
        view = WeeklyView(events, target_timezone=timezone.utc)

        leap_day = datetime(2024, 2, 29, tzinfo=timezone.utc)
        view.set_week(leap_day)

        assert view.start_date.weekday() == 0
        assert view.start_date.year == 2024
        assert view.start_date.month == 2
        assert view.start_date.day == 26

    def test_set_week_with_year_boundary(self):
        """Test jumping to dates near year boundaries."""
        events = []
        view = WeeklyView(events, target_timezone=timezone.utc)

        # New Year's Day 2025 (Wednesday)
        new_year = datetime(2025, 1, 1, tzinfo=timezone.utc)
        view.set_week(new_year)

        assert view.start_date.weekday() == 0
        assert view.start_date.year == 2024
        assert view.start_date.month == 12
        assert view.start_date.day == 30

        # New Year's Eve 2024
        new_years_eve = datetime(2024, 12, 31, tzinfo=timezone.utc)
        view.set_week(new_years_eve)

        assert view.start_date.weekday() == 0
        assert view.start_date.year == 2024
        assert view.start_date.month == 12
        assert view.start_date.day == 30

    def test_set_week_preserves_time_zero(self):
        """Test that set_week resets time to midnight."""
        events = []
        view = WeeklyView(events, target_timezone=timezone.utc)

        afternoon = datetime(2025, 10, 23, 14, 30, 45, tzinfo=timezone.utc)
        view.set_week(afternoon)

        assert view.start_date.hour == 0
        assert view.start_date.minute == 0
        assert view.start_date.second == 0
        assert view.start_date.microsecond == 0

    def test_set_week_with_different_timezones(self):
        """Test that set_week preserves the input date's timezone."""
        events = []
        tz_plus_5 = timezone(timedelta(hours=5, minutes=30))
        view = WeeklyView(events, target_timezone=tz_plus_5)

        # set_week preserves the timezone from the input date
        utc_date = datetime(2025, 10, 23, tzinfo=timezone.utc)
        view.set_week(utc_date)

        assert view.start_date.tzinfo == timezone.utc
        assert view.start_date.weekday() == 0

        # Now set with tz_plus_5
        plus5_date = datetime(2025, 10, 23, tzinfo=tz_plus_5)
        view.set_week(plus5_date)

        assert view.start_date.tzinfo == tz_plus_5
        assert view.start_date.weekday() == 0

    def test_set_week_without_timezone(self):
        """Test jumping to naive datetime."""
        events = []
        view = WeeklyView(events, target_timezone=timezone.utc)

        naive_date = datetime(2025, 10, 23)
        view.set_week(naive_date)

        assert view.start_date.tzinfo == timezone.utc
        assert view.start_date.weekday() == 0

    def test_navigation_chain_consistency(self):
        """Test that multiple navigation operations maintain consistency."""
        events = []
        view = WeeklyView(events, target_timezone=timezone.utc)

        initial_date = datetime(2025, 6, 15, tzinfo=timezone.utc)
        view.set_week(initial_date)

        for _ in range(10):
            view.next_week()

        for _ in range(10):
            view.previous_week()

        expected_monday = initial_date - timedelta(days=initial_date.weekday())
        assert view.start_date.date() == expected_monday.date()
        assert view.start_date.weekday() == 0

    def test_set_week_far_future(self):
        """Test jumping to a far future date."""
        events = []
        view = WeeklyView(events, target_timezone=timezone.utc)

        future_date = datetime(2099, 12, 31, tzinfo=timezone.utc)
        view.set_week(future_date)

        assert view.start_date.weekday() == 0
        assert view.start_date.year == 2099
        assert 1 <= view.start_date.month <= 12

    def test_set_week_far_past(self):
        """Test jumping to a far past date."""
        events = []
        view = WeeklyView(events, target_timezone=timezone.utc)

        past_date = datetime(2000, 1, 1, tzinfo=timezone.utc)
        view.set_week(past_date)

        assert view.start_date.weekday() == 0
        assert view.start_date.year == 1999
        assert view.start_date.month == 12
        assert view.start_date.day == 27
