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


class TestEventNavigation:
    """Test event selection and navigation functionality."""

    def test_get_all_week_events_empty(self):
        """Test getting events from empty week."""
        view = WeeklyView([], target_timezone=timezone.utc)
        events = view._get_all_week_events()

        assert events == []

    def test_get_all_week_events_single(self):
        """Test getting single event."""
        events = [
            {
                "start": datetime(2025, 10, 23, 14, 0, 0, tzinfo=timezone.utc),
                "end": datetime(2025, 10, 23, 15, 0, 0, tzinfo=timezone.utc),
                "summary": "Test Event",
                "location": "Room A",
                "description": "Test description",
            }
        ]
        start = datetime(2025, 10, 20, tzinfo=timezone.utc)
        view = WeeklyView(events, start, timezone.utc)

        week_events = view._get_all_week_events()

        assert len(week_events) == 1
        assert week_events[0]["summary"] == "Test Event"

    def test_get_all_week_events_multiple(self):
        """Test getting multiple events in chronological order."""
        events = [
            {
                "start": datetime(2025, 10, 23, 14, 0, 0, tzinfo=timezone.utc),
                "end": datetime(2025, 10, 23, 15, 0, 0, tzinfo=timezone.utc),
                "summary": "Event 2",
                "location": "",
                "description": "",
            },
            {
                "start": datetime(2025, 10, 22, 10, 0, 0, tzinfo=timezone.utc),
                "end": datetime(2025, 10, 22, 11, 0, 0, tzinfo=timezone.utc),
                "summary": "Event 1",
                "location": "",
                "description": "",
            },
        ]
        start = datetime(2025, 10, 20, tzinfo=timezone.utc)
        view = WeeklyView(events, start, timezone.utc)

        week_events = view._get_all_week_events()

        assert len(week_events) == 2
        # Events should be in chronological order (sorted by filter_events_for_week)
        assert week_events[0]["summary"] == "Event 1"
        assert week_events[1]["summary"] == "Event 2"

    def test_display_event_details(self, capsys):
        """Test displaying event details."""
        event = {
            "start": datetime(2025, 10, 23, 14, 0, 0, tzinfo=timezone.utc),
            "end": datetime(2025, 10, 23, 15, 0, 0, tzinfo=timezone.utc),
            "summary": "Team Meeting",
            "location": "Conference Room A",
            "description": "Weekly team sync",
        }
        view = WeeklyView([], target_timezone=timezone.utc)

        view._display_event_details(event)

        captured = capsys.readouterr()
        assert "Event Details" in captured.out
        assert "Team Meeting" in captured.out
        assert "Conference Room A" in captured.out
        assert "Weekly team sync" in captured.out
        assert "┌" in captured.out
        assert "└" in captured.out

    def test_display_event_details_no_location(self, capsys):
        """Test displaying event without location."""
        event = {
            "start": datetime(2025, 10, 23, 14, 0, 0, tzinfo=timezone.utc),
            "end": datetime(2025, 10, 23, 15, 0, 0, tzinfo=timezone.utc),
            "summary": "Test Event",
            "location": "",
            "description": "",
        }
        view = WeeklyView([], target_timezone=timezone.utc)

        view._display_event_details(event)

        captured = capsys.readouterr()
        assert "Event Details" in captured.out
        assert "Test Event" in captured.out
        assert "Location:" not in captured.out
        assert "┌" in captured.out
        assert "└" in captured.out

    def test_display_with_selection(self, capsys):
        """Test that display shows selection marker."""
        events = [
            {
                "start": datetime(2025, 10, 23, 14, 0, 0, tzinfo=timezone.utc),
                "end": datetime(2025, 10, 23, 15, 0, 0, tzinfo=timezone.utc),
                "summary": "Event 1",
                "location": "",
                "description": "",
            },
            {
                "start": datetime(2025, 10, 24, 10, 0, 0, tzinfo=timezone.utc),
                "end": datetime(2025, 10, 24, 11, 0, 0, tzinfo=timezone.utc),
                "summary": "Event 2",
                "location": "",
                "description": "",
            },
        ]
        start = datetime(2025, 10, 20, tzinfo=timezone.utc)
        view = WeeklyView(events, start, timezone.utc)

        view.display(selected_event_index=0)

        captured = capsys.readouterr()
        # Should show selection marker
        assert "▶" in captured.out

    def test_selected_event_index_initialization(self):
        """Test that selected event index is initialized to 0."""
        view = WeeklyView([], target_timezone=timezone.utc)

        assert view._selected_event_index == 0

    def test_display_event_details_with_calendar_name(self, capsys):
        """Test displaying event with calendar name."""
        event = {
            "start": datetime(2025, 10, 23, 14, 0, 0, tzinfo=timezone.utc),
            "end": datetime(2025, 10, 23, 15, 0, 0, tzinfo=timezone.utc),
            "summary": "Team Meeting",
            "location": "Conference Room A",
            "description": "Weekly team sync",
            "calendar_name": "Work Calendar",
        }
        view = WeeklyView([], target_timezone=timezone.utc)

        view._display_event_details(event)

        captured = capsys.readouterr()
        assert "Calendar:" in captured.out
        assert "Work Calendar" in captured.out

    def test_display_event_details_strips_html(self, capsys):
        """Test that HTML tags are stripped from descriptions."""
        event = {
            "start": datetime(2025, 10, 23, 14, 0, 0, tzinfo=timezone.utc),
            "end": datetime(2025, 10, 23, 15, 0, 0, tzinfo=timezone.utc),
            "summary": "Event with HTML",
            "location": "",
            "description": '<a href="#">Some link</a> and <b>bold text</b>',
        }
        view = WeeklyView([], target_timezone=timezone.utc)

        view._display_event_details(event)

        captured = capsys.readouterr()
        assert "Some link and bold text" in captured.out
        assert "<a href" not in captured.out
        assert "<b>" not in captured.out

    def test_display_event_details_wraps_long_lines(self, capsys):
        """Test that long lines are wrapped properly within the box."""
        import re

        event = {
            "start": datetime(2025, 11, 2, 0, 0, 0, tzinfo=timezone.utc),
            "end": datetime(2025, 11, 3, 0, 0, 0, tzinfo=timezone.utc),
            "summary": "Long date event",
            "location": "",
            "description": "",
            "calendar_name": "Shared",
        }
        view = WeeklyView([], target_timezone=timezone.utc)

        view._display_event_details(event)

        captured = capsys.readouterr()
        lines = captured.out.split("\n")
        ansi_escape = re.compile(r"\x1b\[[0-9;]*m")
        for line in lines:
            clean_line = ansi_escape.sub("", line)
            assert len(clean_line) <= 80, f"Line exceeds 80 chars: {clean_line}"
