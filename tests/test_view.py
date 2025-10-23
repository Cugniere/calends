import pytest
from datetime import datetime, timezone, timedelta
from calends.view import WeeklyView


class TestFilterEventsForWeek:
    def test_filter_events_in_range(self):
        week_start = datetime(2025, 1, 13, 0, 0, 0, tzinfo=timezone.utc)
        events = [
            {
                "start": datetime(2025, 1, 14, 10, 0, 0, tzinfo=timezone.utc),
                "end": datetime(2025, 1, 14, 11, 0, 0, tzinfo=timezone.utc),
                "summary": "In Range",
            },
            {
                "start": datetime(2025, 1, 20, 10, 0, 0, tzinfo=timezone.utc),
                "end": datetime(2025, 1, 20, 11, 0, 0, tzinfo=timezone.utc),
                "summary": "Out of Range",
            },
        ]
        view = WeeklyView(events, week_start)

        filtered = view.filter_events_for_week()

        assert len(filtered) == 1
        day_events = list(filtered.values())[0]
        assert day_events[0]["summary"] == "In Range"

    def test_filter_boundary_events(self):
        week_start = datetime(2025, 1, 13, 0, 0, 0, tzinfo=timezone.utc)
        events = [
            {
                "start": datetime(2025, 1, 13, 0, 0, 0, tzinfo=timezone.utc),
                "end": datetime(2025, 1, 13, 1, 0, 0, tzinfo=timezone.utc),
                "summary": "Start Boundary",
            },
            {
                "start": datetime(2025, 1, 19, 23, 0, 0, tzinfo=timezone.utc),
                "end": datetime(2025, 1, 19, 23, 59, 0, tzinfo=timezone.utc),
                "summary": "End Boundary",
            },
        ]
        view = WeeklyView(events, week_start)

        filtered = view.filter_events_for_week()

        assert len(filtered) == 2

    def test_filter_empty_events(self):
        week_start = datetime(2025, 1, 13, 0, 0, 0, tzinfo=timezone.utc)
        view = WeeklyView([], week_start)

        filtered = view.filter_events_for_week()

        assert len(filtered) == 0

    def test_filter_all_outside_range(self):
        week_start = datetime(2025, 1, 13, 0, 0, 0, tzinfo=timezone.utc)
        events = [
            {
                "start": datetime(2025, 1, 6, 10, 0, 0, tzinfo=timezone.utc),
                "end": datetime(2025, 1, 6, 11, 0, 0, tzinfo=timezone.utc),
                "summary": "Before Week",
            },
            {
                "start": datetime(2025, 1, 27, 10, 0, 0, tzinfo=timezone.utc),
                "end": datetime(2025, 1, 27, 11, 0, 0, tzinfo=timezone.utc),
                "summary": "After Week",
            },
        ]
        view = WeeklyView(events, week_start)

        filtered = view.filter_events_for_week()

        assert len(filtered) == 0


class TestWeeklyViewDisplay:
    def test_display_runs_without_error(self, capsys):
        week_start = datetime(2025, 1, 13, 0, 0, 0, tzinfo=timezone.utc)
        events = [
            {
                "start": datetime(2025, 1, 14, 10, 0, 0, tzinfo=timezone.utc),
                "end": datetime(2025, 1, 14, 11, 0, 0, tzinfo=timezone.utc),
                "summary": "Test Event",
                "location": "Room A",
                "description": "Test",
            }
        ]
        view = WeeklyView(events, week_start)

        view.display()

        captured = capsys.readouterr()
        assert len(captured.out) > 0

    def test_display_empty_week(self, capsys):
        week_start = datetime(2025, 1, 13, 0, 0, 0, tzinfo=timezone.utc)
        view = WeeklyView([], week_start)

        view.display()

        captured = capsys.readouterr()
        assert len(captured.out) > 0
