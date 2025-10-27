import pytest
from datetime import datetime, timezone
from calends.calendar_manager import CalendarManager


class TestCalendarManager:
    def test_init_default(self):
        manager = CalendarManager(show_progress=False)
        assert manager.parser is not None
        assert manager.fetcher is not None
        assert manager.events is not None

    def test_init_with_timezone(self):
        tz = timezone.utc
        manager = CalendarManager(target_timezone=tz, show_progress=False)
        assert manager.parser.target_timezone == tz

    def test_init_with_cache_expiration(self):
        manager = CalendarManager(cache_expiration=300, show_progress=False)
        assert manager.fetcher.cache.expiration == 300

    def test_count_events_empty(self):
        manager = CalendarManager(show_progress=False)
        assert manager.count_events() == 0

    def test_get_all_events_empty(self):
        manager = CalendarManager(show_progress=False)
        assert manager.get_all_events() == []


class TestLoadSource:
    def test_load_source_from_file(self, tmp_path):
        ical_content = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Test//Test//EN
BEGIN:VEVENT
UID:test-event-1@example.com
DTSTART:20250115T140000Z
DTEND:20250115T150000Z
SUMMARY:Team Meeting
LOCATION:Conference Room A
DESCRIPTION:Weekly team sync
END:VEVENT
END:VCALENDAR"""

        test_file = tmp_path / "calendar.ics"
        test_file.write_text(ical_content)

        manager = CalendarManager(show_progress=False)
        manager.load_source(str(test_file))

        assert manager.count_events() == 1
        events = manager.get_all_events()
        assert events[0]["summary"] == "Team Meeting"
        assert events[0]["location"] == "Conference Room A"

    def test_load_source_with_recurring_event(self, tmp_path):
        ical_content = """BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
UID:recurring@example.com
DTSTART:20250113T100000Z
DTEND:20250113T110000Z
SUMMARY:Daily Standup
RRULE:FREQ=DAILY;COUNT=3
END:VEVENT
END:VCALENDAR"""

        test_file = tmp_path / "recurring.ics"
        test_file.write_text(ical_content)

        manager = CalendarManager(show_progress=False)
        manager.load_source(str(test_file))

        assert manager.count_events() == 3

    def test_load_source_with_multiday_event(self, tmp_path):
        ical_content = """BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
UID:multiday@example.com
DTSTART:20250114T090000Z
DTEND:20250116T180000Z
SUMMARY:Conference
LOCATION:Convention Center
END:VEVENT
END:VCALENDAR"""

        test_file = tmp_path / "multiday.ics"
        test_file.write_text(ical_content)

        manager = CalendarManager(show_progress=False)
        manager.load_source(str(test_file))

        assert manager.count_events() == 2

    def test_load_source_nonexistent_file(self, capsys):
        manager = CalendarManager(show_progress=False)
        manager.load_source("/nonexistent/calendar.ics")

        assert manager.count_events() == 0
        captured = capsys.readouterr()
        assert "not found" in captured.err.lower()

    def test_load_source_invalid_file(self, tmp_path, capsys):
        test_file = tmp_path / "invalid.ics"
        test_file.write_text("This is not iCal content")

        manager = CalendarManager(show_progress=False)
        manager.load_source(str(test_file))

        assert manager.count_events() == 0
        captured = capsys.readouterr()
        assert "does not appear to be valid iCal format" in captured.err


class TestLoadSources:
    def test_load_multiple_sources(self, tmp_path):
        ical1 = """BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
UID:event1@example.com
DTSTART:20250115T100000Z
DTEND:20250115T110000Z
SUMMARY:Event 1
END:VEVENT
END:VCALENDAR"""

        ical2 = """BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
UID:event2@example.com
DTSTART:20250116T140000Z
DTEND:20250116T150000Z
SUMMARY:Event 2
END:VEVENT
END:VCALENDAR"""

        file1 = tmp_path / "calendar1.ics"
        file2 = tmp_path / "calendar2.ics"
        file1.write_text(ical1)
        file2.write_text(ical2)

        manager = CalendarManager(show_progress=False)
        manager.load_sources([str(file1), str(file2)])

        assert manager.count_events() == 2
        events = manager.get_all_events()
        summaries = {e["summary"] for e in events}
        assert summaries == {"Event 1", "Event 2"}

    def test_load_sources_empty_list(self):
        manager = CalendarManager(show_progress=False)
        manager.load_sources([])

        assert manager.count_events() == 0

    def test_load_sources_partial_failure(self, tmp_path, capsys):
        ical_valid = """BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
UID:valid@example.com
DTSTART:20250115T100000Z
DTEND:20250115T110000Z
SUMMARY:Valid Event
END:VEVENT
END:VCALENDAR"""

        valid_file = tmp_path / "valid.ics"
        valid_file.write_text(ical_valid)

        manager = CalendarManager(show_progress=False)
        manager.load_sources([str(valid_file), "/nonexistent/invalid.ics"])

        assert manager.count_events() == 1
        captured = capsys.readouterr()
        assert "not found" in captured.err.lower()


class TestTimezoneHandling:
    def test_events_converted_to_target_timezone(self, tmp_path):
        ical_content = """BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
UID:tz-event@example.com
DTSTART:20250115T140000Z
DTEND:20250115T150000Z
SUMMARY:UTC Event
END:VEVENT
END:VCALENDAR"""

        test_file = tmp_path / "calendar.ics"
        test_file.write_text(ical_content)

        from datetime import timedelta

        target_tz = timezone(timedelta(hours=5, minutes=30))
        manager = CalendarManager(target_timezone=target_tz)
        manager.load_source(str(test_file))

        events = manager.get_all_events()
        assert len(events) == 1
        assert events[0]["start"].tzinfo == target_tz

    def test_events_without_timezone_get_target(self, tmp_path):
        ical_content = """BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
UID:no-tz@example.com
DTSTART:20250115T140000
DTEND:20250115T150000
SUMMARY:No TZ Event
END:VEVENT
END:VCALENDAR"""

        test_file = tmp_path / "calendar.ics"
        test_file.write_text(ical_content)

        target_tz = timezone.utc
        manager = CalendarManager(target_timezone=target_tz)
        manager.load_source(str(test_file))

        events = manager.get_all_events()
        assert len(events) == 1
        assert events[0]["start"].tzinfo == target_tz


class TestEventCollection:
    def test_events_accumulate_across_loads(self, tmp_path):
        ical1 = """BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
UID:event1@example.com
DTSTART:20250115T100000Z
DTEND:20250115T110000Z
SUMMARY:Event 1
END:VEVENT
END:VCALENDAR"""

        ical2 = """BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
UID:event2@example.com
DTSTART:20250116T140000Z
DTEND:20250116T150000Z
SUMMARY:Event 2
END:VEVENT
END:VCALENDAR"""

        file1 = tmp_path / "calendar1.ics"
        file2 = tmp_path / "calendar2.ics"
        file1.write_text(ical1)
        file2.write_text(ical2)

        manager = CalendarManager(show_progress=False)
        manager.load_source(str(file1))
        assert manager.count_events() == 1

        manager.load_source(str(file2))
        assert manager.count_events() == 2

    def test_get_all_events_returns_list(self, tmp_path):
        ical_content = """BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
UID:test@example.com
DTSTART:20250115T100000Z
DTEND:20250115T110000Z
SUMMARY:Test Event
END:VEVENT
END:VCALENDAR"""

        test_file = tmp_path / "calendar.ics"
        test_file.write_text(ical_content)

        manager = CalendarManager(show_progress=False)
        manager.load_source(str(test_file))

        events = manager.get_all_events()
        assert isinstance(events, list)
        assert len(events) == 1
        assert isinstance(events[0], dict)


class TestCalendarAliases:
    """Test calendar alias functionality."""

    def test_init_with_aliases(self):
        """Test that aliases are stored correctly on init."""
        aliases = {
            "https://work.example.com/cal.ics": "Work",
            "/path/to/personal.ics": "Personal"
        }
        manager = CalendarManager(aliases=aliases, show_progress=False)

        assert manager.aliases == aliases

    def test_init_without_aliases(self):
        """Test that manager works without aliases."""
        manager = CalendarManager(show_progress=False)

        assert manager.aliases == {}

    def test_get_display_name_with_alias(self):
        """Test that _get_display_name returns alias when available."""
        aliases = {
            "https://work.example.com/cal.ics": "Work Calendar"
        }
        manager = CalendarManager(aliases=aliases, show_progress=False)

        display_name = manager._get_display_name("https://work.example.com/cal.ics")

        assert display_name == "Work Calendar"

    def test_get_display_name_without_alias(self):
        """Test that _get_display_name returns source when no alias."""
        manager = CalendarManager(show_progress=False)

        display_name = manager._get_display_name("short.ics")

        assert display_name == "short.ics"

    def test_get_display_name_truncates_long_source(self):
        """Test that _get_display_name truncates long sources without alias."""
        manager = CalendarManager(show_progress=False)
        long_url = "https://example.com/" + "a" * 100 + "/calendar.ics"

        display_name = manager._get_display_name(long_url)

        assert len(display_name) <= 60
        assert display_name.startswith("...")

    def test_load_source_with_alias(self, tmp_path, capsys):
        """Test that load_source uses alias in output."""
        ical_content = """BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
UID:test@example.com
DTSTART:20250115T140000Z
DTEND:20250115T150000Z
SUMMARY:Test Event
END:VEVENT
END:VCALENDAR"""

        test_file = tmp_path / "calendar.ics"
        test_file.write_text(ical_content)

        aliases = {str(test_file): "My Work Calendar"}
        manager = CalendarManager(aliases=aliases, show_progress=True)
        manager.load_source(str(test_file))

        captured = capsys.readouterr()
        assert "My Work Calendar" in captured.err

    def test_load_sources_with_aliases(self, tmp_path, capsys):
        """Test that load_sources uses aliases for multiple sources."""
        ical_content = """BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
UID:test@example.com
DTSTART:20250115T140000Z
DTEND:20250115T150000Z
SUMMARY:Test Event
END:VEVENT
END:VCALENDAR"""

        file1 = tmp_path / "cal1.ics"
        file2 = tmp_path / "cal2.ics"
        file1.write_text(ical_content)
        file2.write_text(ical_content)

        aliases = {
            str(file1): "Work",
            str(file2): "Personal"
        }
        manager = CalendarManager(aliases=aliases, show_progress=True)
        manager.load_sources([str(file1), str(file2)])

        captured = capsys.readouterr()
        assert "Work" in captured.err
        assert "Personal" in captured.err
