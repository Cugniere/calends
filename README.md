# Calends

A minimalist terminal calendar that displays your iCal events in a clean weekly view with support for recurring events, timezones, and remote calendars.

## Installation

```bash
pip install -e .
```

## Quick Start

```bash
# View local calendar
calends calendar.ics

# View remote calendar
calends https://example.com/calendar.ics

# Use config file (calendars.json or calends.json auto-detected)
calends -c config.json

# View specific week
calends -d 2025-12-25 calendar.ics

# Use specific timezone
calends -tz UTC calendar.ics
calends -tz +05:30 calendar.ics
```

## Configuration

Create `calendars.json` or `calends.json`:

```json
{
  "calendars": [
    "https://example.com/cal1.ics",
    "path/to/cal2.ics"
  ],
  "timezone": "UTC",
  "cache_expiration": 3600
}
```

## Options

- `SOURCE`: iCal file path or URL
- `-c, --config FILE`: Config file path
- `-d, --date YYYY-MM-DD`: Start date (adjusts to Monday)
- `-tz, --timezone TZ`: Timezone (UTC, LOCAL, or offset like +05:30)
- `--no-color`: Disable colors

## Features

- Weekly calendar view
- Support for recurring events (RRULE)
- Multi-day event expansion
- Timezone conversion
- URL caching
- Color-coded display (ongoing/past/future events)

## Testing

```bash
pytest
```
