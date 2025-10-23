import pytest
import json
from datetime import timezone, timedelta
from pathlib import Path
from calends.config import parse_timezone, load_config, find_default_config


class TestParseTimezone:
    def test_parse_utc(self):
        tz = parse_timezone("UTC")
        assert tz == timezone.utc

    def test_parse_positive_offset(self):
        tz = parse_timezone("+05:30")
        expected = timezone(timedelta(hours=5, minutes=30))
        assert tz == expected

    def test_parse_negative_offset(self):
        tz = parse_timezone("-08:00")
        expected = timezone(timedelta(hours=-8))
        assert tz == expected

    def test_parse_local(self):
        tz = parse_timezone("LOCAL")
        assert tz is None

    def test_parse_zero_offset(self):
        tz = parse_timezone("+00:00")
        assert tz == timezone.utc


class TestLoadConfig:
    def test_load_valid_config(self, tmp_path):
        config_file = tmp_path / "config.json"
        config_data = {
            "calendars": ["https://example.com/cal.ics"],
            "timezone": "UTC",
            "cache_expiration": 7200,
        }
        config_file.write_text(json.dumps(config_data))

        calendars, timezone_str, cache_exp = load_config(str(config_file))

        assert calendars == ["https://example.com/cal.ics"]
        assert timezone_str == "UTC"
        assert cache_exp == 7200

    def test_load_config_with_defaults(self, tmp_path):
        config_file = tmp_path / "config.json"
        config_data = {"calendars": ["calendar.ics"]}
        config_file.write_text(json.dumps(config_data))

        calendars, timezone_str, cache_exp = load_config(str(config_file))

        assert calendars == ["calendar.ics"]
        assert cache_exp == 60

    def test_load_nonexistent_config(self):
        calendars, timezone_str, cache_exp = load_config(
            "/nonexistent/path/config.json"
        )
        assert calendars == []


class TestFindDefaultConfig:
    def test_find_calendars_json(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        config_file = tmp_path / "calendars.json"
        config_file.write_text('{"sources": []}')

        result = find_default_config()

        assert result == "calendars.json"

    def test_find_calends_json(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        config_file = tmp_path / "calends.json"
        config_file.write_text('{"sources": []}')

        result = find_default_config()

        assert result == "calends.json"

    def test_no_default_config(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)

        result = find_default_config()

        assert result is None

    def test_calendars_priority_over_calends(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        calendars = tmp_path / "calendars.json"
        calends = tmp_path / "calends.json"
        calendars.write_text('{"sources": []}')
        calends.write_text('{"sources": []}')

        result = find_default_config()

        assert result == "calendars.json"
