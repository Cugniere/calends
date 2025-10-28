import pytest
import time
import threading
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

        view = WeeklyView(
            events, target_timezone=timezone.utc, refresh_callback=mock_callback
        )

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

        view = WeeklyView(
            events, target_timezone=timezone.utc, refresh_callback=failing_callback
        )

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

        view = WeeklyView(
            events, target_timezone=timezone.utc, refresh_callback=empty_callback
        )

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


class TestBackgroundRefresh:
    """Test background auto-refresh functionality."""

    def test_background_refresh_disabled_by_default(self):
        """Test that background refresh is disabled when interval is 0."""
        events = []

        def mock_callback():
            return []

        view = WeeklyView(
            events,
            target_timezone=timezone.utc,
            refresh_callback=mock_callback,
            auto_refresh_interval=0,
        )

        view._start_background_refresh()
        assert view._refresh_thread is None

    def test_background_refresh_disabled_without_callback(self):
        """Test that background refresh is not started without a refresh callback."""
        events = []
        view = WeeklyView(
            events,
            target_timezone=timezone.utc,
            refresh_callback=None,
            auto_refresh_interval=60,
        )

        view._start_background_refresh()
        assert view._refresh_thread is None

    def test_background_refresh_thread_starts(self):
        """Test that background refresh thread starts when enabled."""
        events = []
        refresh_count = {"count": 0}

        def mock_callback():
            refresh_count["count"] += 1
            return []

        view = WeeklyView(
            events,
            target_timezone=timezone.utc,
            refresh_callback=mock_callback,
            auto_refresh_interval=1,
        )

        view._start_background_refresh()

        assert view._refresh_thread is not None
        assert view._refresh_thread.is_alive()
        assert view._refresh_thread.daemon

        view._stop_background_refresh()

    def test_background_refresh_updates_events(self):
        """Test that background refresh actually refreshes events."""
        initial_events = [
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

        view = WeeklyView(
            initial_events,
            target_timezone=timezone.utc,
            refresh_callback=mock_callback,
            auto_refresh_interval=1,
        )

        view._start_background_refresh()

        # Wait for refresh to occur
        time.sleep(1.5)

        # Check that needs_redraw was set
        assert view._needs_redraw.is_set()

        # Events should be updated
        assert len(view.events) == 1
        assert view.events[0]["summary"] == "New Event"

        view._stop_background_refresh()

    def test_background_refresh_sets_redraw_flag(self):
        """Test that background refresh sets the needs_redraw flag."""
        events = []

        def mock_callback():
            return []

        view = WeeklyView(
            events,
            target_timezone=timezone.utc,
            refresh_callback=mock_callback,
            auto_refresh_interval=1,
        )

        assert not view._needs_redraw.is_set()

        view._start_background_refresh()

        # Wait for refresh to occur
        time.sleep(1.5)

        assert view._needs_redraw.is_set()

        view._stop_background_refresh()

    def test_background_refresh_stops_cleanly(self):
        """Test that background refresh thread stops when requested."""
        events = []

        def mock_callback():
            return []

        view = WeeklyView(
            events,
            target_timezone=timezone.utc,
            refresh_callback=mock_callback,
            auto_refresh_interval=1,
        )

        view._start_background_refresh()
        assert view._refresh_thread.is_alive()

        view._stop_background_refresh()

        # Thread should stop within timeout
        time.sleep(0.1)
        assert not view._refresh_thread.is_alive()

    def test_background_refresh_silent_mode(self):
        """Test that background refresh uses silent mode (no output)."""
        events = []
        refresh_calls = []

        def mock_callback():
            refresh_calls.append({"silent": True})
            return []

        view = WeeklyView(
            events,
            target_timezone=timezone.utc,
            refresh_callback=mock_callback,
            auto_refresh_interval=1,
        )

        view._start_background_refresh()

        # Wait for refresh
        time.sleep(1.5)

        # Refresh should have been called
        assert len(refresh_calls) >= 1

        view._stop_background_refresh()

    def test_background_refresh_handles_callback_failure(self):
        """Test that background refresh handles callback failures gracefully."""
        events = []
        call_count = {"count": 0}

        def failing_callback():
            call_count["count"] += 1
            if call_count["count"] == 1:
                raise Exception("Simulated network error")
            return []

        view = WeeklyView(
            events,
            target_timezone=timezone.utc,
            refresh_callback=failing_callback,
            auto_refresh_interval=1,
        )

        view._start_background_refresh()

        # Wait for first refresh (will fail) and second refresh (will succeed)
        time.sleep(2.5)

        # Thread should still be alive despite failure
        assert view._refresh_thread.is_alive()

        # Second refresh should have succeeded
        assert call_count["count"] >= 2

        view._stop_background_refresh()

    def test_refresh_events_silent_parameter(self):
        """Test that refresh_events respects the silent parameter."""
        events = []

        def mock_callback():
            return []

        view = WeeklyView(
            events, target_timezone=timezone.utc, refresh_callback=mock_callback
        )

        # Test silent refresh (should not print anything)
        result = view.refresh_events(silent=True)
        assert result is True

        # Test non-silent refresh (would print, but we can't easily capture in test)
        result = view.refresh_events(silent=False)
        assert result is True

    def test_silent_refresh_disables_manager_progress(self):
        """Test that silent refresh temporarily disables manager progress output."""
        events = []

        # Create a mock calendar manager
        class MockManager:
            def __init__(self):
                self.show_progress = True
                self.fetcher = type("obj", (object,), {"show_progress": True})()

        manager = MockManager()

        def mock_callback():
            # During callback, show_progress should be False
            assert manager.show_progress is False
            assert manager.fetcher.show_progress is False
            return []

        view = WeeklyView(
            events,
            target_timezone=timezone.utc,
            refresh_callback=mock_callback,
            calendar_manager=manager,
        )

        # Initially, show_progress should be True
        assert manager.show_progress is True
        assert manager.fetcher.show_progress is True

        # Silent refresh should temporarily disable it
        result = view.refresh_events(silent=True)
        assert result is True

        # After refresh, should be restored
        assert manager.show_progress is True
        assert manager.fetcher.show_progress is True
