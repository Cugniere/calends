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

        calendars, timezone_str, cache_exp, aliases = load_config(str(config_file))

        assert calendars == ["https://example.com/cal.ics"]
        assert timezone_str == "UTC"
        assert cache_exp == 7200
        assert aliases is None

    def test_load_config_with_defaults(self, tmp_path):
        config_file = tmp_path / "config.json"
        config_data = {"calendars": ["calendar.ics"]}
        config_file.write_text(json.dumps(config_data))

        calendars, timezone_str, cache_exp, aliases = load_config(str(config_file))

        assert calendars == ["calendar.ics"]
        assert cache_exp == 60
        assert aliases is None

    def test_load_nonexistent_config(self):
        with pytest.raises(FileNotFoundError):
            load_config("/nonexistent/path/config.json")

    def test_load_config_with_aliases_dict(self, tmp_path):
        """Test loading config with new dict format (aliases)."""
        config_file = tmp_path / "config.json"
        config_data = {
            "calendars": {
                "Work": "https://work.example.com/cal.ics",
                "Personal": "/path/to/personal.ics",
            },
            "timezone": "UTC",
            "cache_expiration": 3600,
        }
        config_file.write_text(json.dumps(config_data))

        calendars, timezone_str, cache_exp, aliases = load_config(str(config_file))

        assert len(calendars) == 2
        assert "https://work.example.com/cal.ics" in calendars
        assert "/path/to/personal.ics" in calendars
        assert timezone_str == "UTC"
        assert cache_exp == 3600
        assert aliases is not None
        assert aliases["https://work.example.com/cal.ics"] == "Work"
        assert aliases["/path/to/personal.ics"] == "Personal"

    def test_load_config_with_aliases_dict_defaults(self, tmp_path):
        """Test loading config with aliases and default values."""
        config_file = tmp_path / "config.json"
        config_data = {"calendars": {"MyCalendar": "calendar.ics"}}
        config_file.write_text(json.dumps(config_data))

        calendars, timezone_str, cache_exp, aliases = load_config(str(config_file))

        assert calendars == ["calendar.ics"]
        assert timezone_str is None
        assert cache_exp == 60
        assert aliases == {"calendar.ics": "MyCalendar"}

    def test_load_config_empty_dict_fails(self, tmp_path):
        """Test that empty calendars dict raises error."""
        config_file = tmp_path / "config.json"
        config_data = {"calendars": {}}
        config_file.write_text(json.dumps(config_data))

        with pytest.raises(ValueError, match="cannot be empty"):
            load_config(str(config_file))

    def test_load_config_invalid_alias_value(self, tmp_path):
        """Test that non-string calendar source raises error."""
        config_file = tmp_path / "config.json"
        config_data = {"calendars": {"BadCalendar": 123}}
        config_file.write_text(json.dumps(config_data))

        with pytest.raises(ValueError, match="must be a string"):
            load_config(str(config_file))


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

    def test_find_home_config(self, tmp_path, monkeypatch):
        """Test finding config in home directory."""
        monkeypatch.chdir(tmp_path)
        # Mock home directory
        home_dir = tmp_path / "home"
        home_dir.mkdir()
        monkeypatch.setattr(Path, "home", lambda: home_dir)

        # Create config in home directory
        home_config = home_dir / ".calends.json"
        home_config.write_text('{"calendars": []}')

        result = find_default_config()

        assert result == str(home_config)

    def test_find_config_directory(self, tmp_path, monkeypatch):
        """Test finding config in user config directory."""
        monkeypatch.chdir(tmp_path)
        # Mock home directory
        home_dir = tmp_path / "home"
        home_dir.mkdir()
        monkeypatch.setattr(Path, "home", lambda: home_dir)

        # Create config in config directory
        config_dir = home_dir / ".config" / "calends"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "config.json"
        config_file.write_text('{"calendars": []}')

        result = find_default_config()

        assert result == str(config_file)

    def test_current_dir_priority(self, tmp_path, monkeypatch):
        """Test that current directory has priority over home."""
        monkeypatch.chdir(tmp_path)
        # Mock home directory
        home_dir = tmp_path / "home"
        home_dir.mkdir()
        monkeypatch.setattr(Path, "home", lambda: home_dir)

        # Create config in both locations
        current_config = tmp_path / "calendars.json"
        current_config.write_text('{"calendars": ["current"]}')

        home_config = home_dir / ".calends.json"
        home_config.write_text('{"calendars": ["home"]}')

        result = find_default_config()

        # Current directory should win
        assert result == "calendars.json"

    def test_home_priority_over_config_dir(self, tmp_path, monkeypatch):
        """Test that home directory has priority over config directory."""
        monkeypatch.chdir(tmp_path)
        # Mock home directory
        home_dir = tmp_path / "home"
        home_dir.mkdir()
        monkeypatch.setattr(Path, "home", lambda: home_dir)

        # Create config in both locations
        home_config = home_dir / ".calends.json"
        home_config.write_text('{"calendars": ["home"]}')

        config_dir = home_dir / ".config" / "calends"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "config.json"
        config_file.write_text('{"calendars": ["config_dir"]}')

        result = find_default_config()

        # Home directory should win
        assert result == str(home_config)

    def test_calendars_priority_over_calends(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        calendars = tmp_path / "calendars.json"
        calends = tmp_path / "calends.json"
        calendars.write_text('{"sources": []}')
        calends.write_text('{"sources": []}')

        result = find_default_config()

        assert result == "calendars.json"
