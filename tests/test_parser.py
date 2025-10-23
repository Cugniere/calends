import pytest
from datetime import datetime, timezone, timedelta
from calends.parser import ICalParser


class TestParseDateTime:
    def test_parse_utc_datetime(self):
        parser = ICalParser()
        result = parser.parse_datetime("20250115T140000Z")
        expected = datetime(2025, 1, 15, 14, 0, 0, tzinfo=timezone.utc)
        assert result == expected

    def test_parse_date_only(self):
        parser = ICalParser()
        result = parser.parse_datetime("20250115")
        assert result.date() == datetime(2025, 1, 15).date()

    def test_parse_with_timezone(self):
        parser = ICalParser(timezone.utc)
        result = parser.parse_datetime("20250115T140000Z")
        expected = datetime(2025, 1, 15, 14, 0, 0, tzinfo=timezone.utc)
        assert result == expected

    def test_parse_local_time_with_tz(self):
        tz = timezone(timedelta(hours=5, minutes=30))
        parser = ICalParser(tz)
        result = parser.parse_datetime("DTSTART:20250115T140000")
        assert result is not None


class TestParseEvent:
    def test_parse_simple_event(self, sample_ics_simple):
        parser = ICalParser()
        lines = sample_ics_simple.split("\n")

        event_lines = []
        in_event = False
        for line in lines:
            if line.startswith("BEGIN:VEVENT"):
                in_event = True
            elif line.startswith("END:VEVENT"):
                event_lines.append(line)
                break
            elif in_event:
                event_lines.append(line)

        event = parser.parse_event(event_lines)

        assert event["summary"] == "Team Meeting"
        assert event["location"] == "Conference Room A"
        assert event["description"] == "Weekly team sync"
        assert "start" in event
        assert "end" in event

    def test_parse_event_with_missing_fields(self):
        parser = ICalParser()
        event_lines = [
            "UID:minimal@example.com",
            "DTSTART:20250115T140000Z",
            "DTEND:20250115T150000Z",
            "SUMMARY:Minimal Event",
            "END:VEVENT",
        ]

        event = parser.parse_event(event_lines)

        assert event["summary"] == "Minimal Event"
        assert event["location"] == ""
        assert event["description"] == ""


class TestParseRRule:
    def test_parse_daily_rrule(self):
        parser = ICalParser()
        rrule = parser.parse_rrule("RRULE:FREQ=DAILY;UNTIL=20250120T110000Z")

        assert rrule["FREQ"] == "DAILY"
        assert "UNTIL" in rrule

    def test_parse_weekly_rrule_with_interval(self):
        parser = ICalParser()
        rrule = parser.parse_rrule("RRULE:FREQ=WEEKLY;INTERVAL=2;COUNT=10")

        assert rrule["FREQ"] == "WEEKLY"
        assert rrule["INTERVAL"] == "2"
        assert rrule["COUNT"] == "10"

    def test_parse_monthly_rrule(self):
        parser = ICalParser()
        rrule = parser.parse_rrule("RRULE:FREQ=MONTHLY;UNTIL=20251215T000000Z")

        assert rrule["FREQ"] == "MONTHLY"
        assert "UNTIL" in rrule


class TestExpandRecurringEvent:
    def test_expand_daily_recurring(self):
        parser = ICalParser()
        event = {
            "start": datetime(2025, 1, 13, 10, 0, 0, tzinfo=timezone.utc),
            "end": datetime(2025, 1, 13, 11, 0, 0, tzinfo=timezone.utc),
            "summary": "Daily Standup",
            "location": "",
            "description": "",
        }
        rrule = {"FREQ": "DAILY", "UNTIL": "20250116T110000Z"}

        instances = parser.expand_recurring_event(event, rrule, max_instances=100)

        assert len(instances) == 4
        assert instances[0]["start"].day == 13
        assert instances[1]["start"].day == 14
        assert instances[2]["start"].day == 15
        assert instances[3]["start"].day == 16

    def test_expand_weekly_recurring(self):
        parser = ICalParser()
        event = {
            "start": datetime(2025, 1, 6, 14, 0, 0, tzinfo=timezone.utc),
            "end": datetime(2025, 1, 6, 15, 0, 0, tzinfo=timezone.utc),
            "summary": "Weekly Meeting",
            "location": "",
            "description": "",
        }
        rrule = {"FREQ": "WEEKLY", "UNTIL": "20250127T150000Z"}

        instances = parser.expand_recurring_event(event, rrule, max_instances=100)

        assert len(instances) == 4
        assert (instances[1]["start"] - instances[0]["start"]).days == 7

    def test_expand_with_interval(self):
        parser = ICalParser()
        event = {
            "start": datetime(2025, 1, 6, 14, 0, 0, tzinfo=timezone.utc),
            "end": datetime(2025, 1, 6, 15, 0, 0, tzinfo=timezone.utc),
            "summary": "Bi-weekly Meeting",
            "location": "",
            "description": "",
        }
        rrule = {"FREQ": "WEEKLY", "UNTIL": "20250203T150000Z", "INTERVAL": "2"}

        instances = parser.expand_recurring_event(event, rrule, max_instances=100)

        assert len(instances) == 3
        assert (instances[1]["start"] - instances[0]["start"]).days == 14


class TestExpandMultidayEvents:
    def test_expand_multiday_event(self):
        from calends.event_collection import EventCollection

        collection = EventCollection()
        collection.events = [
            {
                "start": datetime(2025, 1, 14, 9, 0, 0, tzinfo=timezone.utc),
                "end": datetime(2025, 1, 16, 18, 0, 0, tzinfo=timezone.utc),
                "summary": "Conference",
                "location": "Convention Center",
                "description": "",
            }
        ]

        collection.expand_multiday_events()

        assert len(collection.events) == 2
        assert collection.events[0]["start"].day == 14
        assert collection.events[1]["start"].day == 15

    def test_single_day_event_unchanged(self):
        from calends.event_collection import EventCollection

        collection = EventCollection()
        collection.events = [
            {
                "start": datetime(2025, 1, 15, 14, 0, 0, tzinfo=timezone.utc),
                "end": datetime(2025, 1, 15, 15, 0, 0, tzinfo=timezone.utc),
                "summary": "Meeting",
                "location": "",
                "description": "",
            }
        ]

        collection.expand_multiday_events()

        assert len(collection.events) == 1
        assert collection.events[0]["summary"] == "Meeting"


class TestUnfoldLines:
    def test_unfold_continuation_line(self):
        parser = ICalParser()
        content = (
            "DESCRIPTION:This is a long description\n that continues on the next line"
        )

        result = parser.unfold_lines(content)

        assert len(result) == 1
        assert (
            result[0]
            == "DESCRIPTION:This is a long descriptionthat continues on the next line"
        )

    def test_unfold_multiple_continuations(self):
        parser = ICalParser()
        content = "SUMMARY:Event\nDESCRIPTION:Line one\n line two\n line three\nLOCATION:Room A"

        result = parser.unfold_lines(content)

        assert len(result) == 3
        assert "DESCRIPTION:Line one" in result[1]

    def test_no_folding(self):
        parser = ICalParser()
        content = "SUMMARY:Simple Event\nLOCATION:Room A"

        result = parser.unfold_lines(content)

        assert len(result) == 2
