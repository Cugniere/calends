import pytest
from datetime import datetime, timezone
from pathlib import Path


@pytest.fixture
def sample_ics_simple():
    return """BEGIN:VCALENDAR
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


@pytest.fixture
def sample_ics_recurring():
    return """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Test//Test//EN
BEGIN:VEVENT
UID:recurring-event@example.com
DTSTART:20250113T100000Z
DTEND:20250113T110000Z
SUMMARY:Daily Standup
RRULE:FREQ=DAILY;UNTIL=20250120T110000Z
END:VEVENT
END:VCALENDAR"""


@pytest.fixture
def sample_ics_multiday():
    return """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Test//Test//EN
BEGIN:VEVENT
UID:multiday-event@example.com
DTSTART:20250114T090000Z
DTEND:20250116T180000Z
SUMMARY:Conference
LOCATION:Convention Center
END:VEVENT
END:VCALENDAR"""


@pytest.fixture
def sample_config():
    return {
        "sources": ["https://example.com/calendar.ics"],
        "timezone": "UTC",
        "cache_expiry": 3600,
    }


@pytest.fixture
def temp_cache_dir(tmp_path):
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    return cache_dir
