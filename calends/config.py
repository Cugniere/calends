import os
import sys
import json
import re
from datetime import timedelta, timezone
from typing import Optional


def find_default_config() -> Optional[str]:
    for name in ["calendars.json", "calends.json"]:
        if os.path.isfile(name):
            return name
    return None


def parse_timezone(tz_string: Optional[str]) -> Optional[timezone]:
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
    try:
        with open(path, encoding="utf-8") as f:
            cfg = json.load(f)
        if not isinstance(cfg.get("calendars"), list):
            raise ValueError("'calendars' must be a list")

        calendars: list[str] = cfg["calendars"]
        timezone_str: Optional[str] = cfg.get("timezone")
        cache_expiration: int = int(cfg.get("cache_expiration", 60))

        return calendars, timezone_str, cache_expiration
    except Exception as e:
        print(f"Error loading config: {e}", file=sys.stderr)
        return [], None, 60
