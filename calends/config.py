"""Configuration file loading and timezone parsing utilities."""

import os
import sys
import json
import re
from datetime import timedelta, timezone
from typing import Optional
from pathlib import Path
from .constants import DEFAULT_CONFIG_FILES, DEFAULT_CACHE_EXPIRATION_CONFIG


def find_default_config() -> Optional[str]:
    """
    Find a default configuration file in multiple locations.

    Searches for configuration files in priority order:
    1. Current directory: ./calendars.json, ./calends.json
    2. User home directory: ~/.calends.json
    3. User config directory:
       - Linux/macOS: ~/.config/calends/config.json
       - macOS: ~/Library/Application Support/calends/config.json
       - Windows: %APPDATA%/calends/config.json

    Returns:
        Path to the first found config file, or None if none found
    """
    # 1. Check current directory first (backward compatibility)
    for name in DEFAULT_CONFIG_FILES:
        if os.path.isfile(name):
            return name

    # 2. Check user home directory
    home = Path.home()
    home_config = home / ".calends.json"
    if home_config.is_file():
        return str(home_config)

    # 3. Check platform-specific config directory
    config_dir = _get_config_directory()
    if config_dir:
        config_file = config_dir / "config.json"
        if config_file.is_file():
            return str(config_file)

    return None


def _get_config_directory() -> Optional[Path]:
    """
    Get the platform-specific configuration directory for calends.

    Returns:
        Path to config directory, or None if it cannot be determined
    """
    home = Path.home()

    # Check XDG_CONFIG_HOME first (Linux/Unix standard)
    xdg_config = os.environ.get("XDG_CONFIG_HOME")
    if xdg_config:
        return Path(xdg_config) / "calends"

    # Platform-specific defaults
    if sys.platform == "darwin":
        # macOS: prefer XDG, fallback to Application Support
        xdg_default = home / ".config" / "calends"
        if xdg_default.exists():
            return xdg_default
        return home / "Library" / "Application Support" / "calends"
    elif sys.platform == "win32":
        # Windows: use APPDATA
        appdata = os.environ.get("APPDATA")
        if appdata:
            return Path(appdata) / "calends"
        return home / "AppData" / "Roaming" / "calends"
    else:
        # Linux and other Unix-like systems
        return home / ".config" / "calends"


def parse_timezone(tz_string: Optional[str]) -> Optional[timezone]:
    """
    Parse a timezone string into a timezone object.

    Supports:
    - "UTC" or "GMT"
    - "LOCAL" (returns None for system local time)
    - Offset format: "+05:30", "-08:00", etc.

    Args:
        tz_string: Timezone string to parse

    Returns:
        Parsed timezone object, or None for local/invalid timezones
    """
    if not tz_string:
        return None
    s = tz_string.strip().upper()
    if s in ("UTC", "GMT"):
        return timezone.utc
    if s == "LOCAL":
        return None
    m = re.match(r"^([+-])(\d{2}):?(\d{2})$", s)
    if m:
        sign = 1 if m[1] == "+" else -1
        return timezone(sign * timedelta(hours=int(m[2]), minutes=int(m[3])))
    print(f"Warning: Invalid timezone '{tz_string}', using local.", file=sys.stderr)
    return None


def load_config(
    path: str,
) -> tuple[list[str], Optional[str], int, Optional[dict[str, str]]]:
    """
    Load calendar configuration from a JSON file.

    Expected JSON structure (new format with aliases):
    {
        "calendars": {
            "Work": "https://work.example.com/calendar.ics",
            "Personal": "/path/to/personal.ics"
        },
        "timezone": "UTC" or "+05:30",
        "cache_expiration": 3600
    }

    Or old format (backward compatible):
    {
        "calendars": ["url1", "url2", ...],
        "timezone": "UTC" or "+05:30",
        "cache_expiration": 3600
    }

    Args:
        path: Path to the JSON configuration file

    Returns:
        Tuple of (calendar_sources, timezone_string, cache_expiration, aliases_dict)
        aliases_dict maps source URL/path to friendly name, or None if old format

    Raises:
        FileNotFoundError: If config file doesn't exist
        PermissionError: If config file can't be read
        ValueError: If config format is invalid
    """
    try:
        with open(path, encoding="utf-8") as f:
            cfg = json.load(f)
    except FileNotFoundError:
        raise
    except PermissionError:
        raise
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON format: {e}")
    except Exception as e:
        raise ValueError(f"Failed to read config file: {e}")

    if not isinstance(cfg, dict):
        raise ValueError("Config file must contain a JSON object")

    if "calendars" not in cfg:
        raise ValueError("Config file must contain 'calendars' field")

    calendars_field = cfg.get("calendars")
    calendars: list[str] = []
    aliases: Optional[dict[str, str]] = None

    # Support both dict (new format with aliases) and list (old format)
    if isinstance(calendars_field, dict):
        # New format: {"alias": "source", ...}
        if not calendars_field:
            raise ValueError("'calendars' dict cannot be empty")
        aliases = {}
        for alias, source in calendars_field.items():
            if not isinstance(source, str):
                raise ValueError(f"Calendar source for '{alias}' must be a string")
            calendars.append(source)
            aliases[source] = alias
    elif isinstance(calendars_field, list):
        # Old format: ["source1", "source2", ...]
        calendars = calendars_field
        if not calendars:
            raise ValueError("'calendars' list cannot be empty")
        aliases = None
    else:
        raise ValueError("'calendars' must be a list or dict")

    timezone_str: Optional[str] = cfg.get("timezone")

    try:
        cache_expiration: int = int(
            cfg.get("cache_expiration", DEFAULT_CACHE_EXPIRATION_CONFIG)
        )
        if cache_expiration < 0:
            raise ValueError("'cache_expiration' must be non-negative")
    except (ValueError, TypeError) as e:
        raise ValueError(f"Invalid 'cache_expiration' value: {e}")

    return calendars, timezone_str, cache_expiration, aliases
