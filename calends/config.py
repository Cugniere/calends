"""Configuration file loading and timezone parsing utilities."""

import os
import sys
import json
import re
from datetime import timedelta, timezone
from typing import Optional
from .constants import DEFAULT_CONFIG_FILES, DEFAULT_CACHE_EXPIRATION_CONFIG


def find_default_config() -> Optional[str]:
    """
    Find a default configuration file in the current directory.

    Searches for configuration files in priority order.

    Returns:
        Path to the first found config file, or None if none found
    """
    for name in DEFAULT_CONFIG_FILES:
        if os.path.isfile(name):
            return name
    return None


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


def load_config(path: str) -> tuple[list[str], Optional[str], int]:
    """
    Load calendar configuration from a JSON file.

    Expected JSON structure:
    {
        "calendars": ["url1", "url2", ...],
        "timezone": "UTC" or "+05:30",
        "cache_expiration": 3600
    }

    Args:
        path: Path to the JSON configuration file

    Returns:
        Tuple of (calendar_sources, timezone_string, cache_expiration)

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

    if not isinstance(cfg.get("calendars"), list):
        raise ValueError("'calendars' must be a list")

    calendars: list[str] = cfg["calendars"]

    if not calendars:
        raise ValueError("'calendars' list cannot be empty")

    timezone_str: Optional[str] = cfg.get("timezone")

    try:
        cache_expiration: int = int(
            cfg.get("cache_expiration", DEFAULT_CACHE_EXPIRATION_CONFIG)
        )
        if cache_expiration < 0:
            raise ValueError("'cache_expiration' must be non-negative")
    except (ValueError, TypeError) as e:
        raise ValueError(f"Invalid 'cache_expiration' value: {e}")

    return calendars, timezone_str, cache_expiration
