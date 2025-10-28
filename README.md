# Calends

A minimalist terminal calendar that displays your iCal events in a clean weekly view with support for recurring events, timezones, and remote calendars.

```
      ════════════════════════════════════════════════════════════════════════════════
                                  Week 43, October 2025
      ════════════════════════════════════════════════════════════════════════════════


      Monday, Oct 20
      ────────────────────────────────────────────────────────────────────────────────
        No events

      Tuesday, Oct 21
      ────────────────────────────────────────────────────────────────────────────────
        14:40 - 15:40  Catch up with Daniel
        15:40 - 16:40  Prepare meetup Low-Code/No-Code
        18:30 - 20:30  Meetup Low-Code/No-Code

      Wednesday, Oct 22
      ────────────────────────────────────────────────────────────────────────────────
        18:30 - 21:30  Dinner at Gabriel's

      Thursday, Oct 23
      ────────────────────────────────────────────────────────────────────────────────
        All day        Work from home
        12:00 - 13:00  Lunch with Mitzy
        15:15 - 16:15  Dentist appointment

      Friday, Oct 24
      ────────────────────────────────────────────────────────────────────────────────
      ▶ 14:30 - 15:30  Dentist appointment
                        ⚲ 36, rue du Louvre, Paris (75001)

      Saturday, Oct 25
      ────────────────────────────────────────────────────────────────────────────────
        11:30 - 12:30  Lunch with Alexander

      Sunday, Oct 26
      ────────────────────────────────────────────────────────────────────────────────
        No events

      ════════════════════════════════════════════════════════════════════════════════
                                      Total events: 9

        [↑↓]select  [n]ext  [p]revious  [t]oday  [j]ump  [r]efresh  [h]elp  [q]uit

      ┌─────────────────────────────── Event Details ────────────────────────────────┐
      │ Title: Day                                                                   │
      │ Calendar: Personal                                                           │
      │ Time: Friday, October 24, 2025 at 14:30 - 15:30                              │
      │ Location: 36, rue du Louvre, Paris (75001)                                   │
      │ Description: 36, rue du Louvre, Paris, France                                │
      │              2nd floor, door on the left                                     │
      └──────────────────────────────────────────────────────────────────────────────┘
```

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

# Interactive mode with event selection and details
calends -i calendar.ics

# Use config file (auto-detected in current directory)
calends

# Or specify config file
calends -c config.json

# View specific week
calends -d 2025-12-25 calendar.ics

# Use specific timezone
calends -tz UTC calendar.ics
calends -tz +05:30 calendar.ics

# Cache management
calends --cache-info        # Show cache statistics
calends --clear-cache       # Clear the cache
```

### Interactive Mode

In interactive mode (`-i`), you can:
- Navigate between weeks and select events
- View detailed event information in a formatted box
- See calendar names (when using aliases)
- Auto-refresh calendars in the background
- Jump to any date quickly

The event details panel shows:
```
┌─────────────────────────────── Event Details ────────────────────────────────┐
│ Title: Team Meeting                                                          │
│ Calendar: Work                                                               │
│ Time: Monday, October 27, 2025 at 14:00 - 15:00                             │
│ Location: Conference Room A                                                  │
│ Attendees: Alice, Bob, Charlie                                               │
│ Description: Weekly team sync to discuss project progress                    │
└──────────────────────────────────────────────────────────────────────────────┘
```

## Configuration

Create `calendars.json` or `calends.json` in your current directory. The config file is auto-detected.

### Format

```json
{
  "calendars": {
    "Work": "https://example.com/work.ics",
    "Personal": "/path/to/personal.ics",
    "Shared": "https://example.com/shared.ics"
  },
  "timezone": "UTC",
  "cache_expiration": 3600,
  "auto_refresh_interval": 300
}
```

**Configuration Options:**
- `calendars`: Dictionary mapping names to sources
- `timezone`: UTC, LOCAL, or offset like +05:30 (default: LOCAL)
- `cache_expiration`: Cache duration in seconds (default: 3600)
- `auto_refresh_interval`: Auto-refresh interval in seconds for interactive mode (default: 300, set to 0 to disable)

## Options

- `SOURCE`: iCal file path or URL
- `-c, --config FILE`: Config file path
- `-d, --date YYYY-MM-DD`: Start date (adjusts to Monday)
- `-tz, --timezone TZ`: Timezone (UTC, LOCAL, or offset like +05:30)
- `-i, --interactive`: Interactive mode for week navigation
- `--no-color`: Disable colors
- `--no-progress`: Disable progress indicators
- `--cache-info`: Display cache statistics
- `--clear-cache`: Clear the calendar cache

## Features

### Display & Navigation
- Clean weekly calendar view with centered headers
- **Interactive navigation** with keyboard shortcuts:
  - ↑/↓: Select events
  - n/→/Space: Next week
  - p/←: Previous week
  - t: Today (current week)
  - j: Jump to specific date
  - r: Refresh calendars
  - h/?: Help
  - q/ESC: Quit
- **Event details panel** with bordered box display showing:
  - Title, calendar name, time, location
  - Attendees list (from ATTENDEE fields)
  - Description with HTML tags stripped
  - Color-coded labels (green) for better readability
- Color-coded events (ongoing/past/future)
- Selection marker (▶) for current event

### Calendar Features
- Support for recurring events (RRULE: DAILY, WEEKLY, MONTHLY, YEARLY)
- Multi-day event expansion
- Timezone conversion (UTC, LOCAL, or custom offsets)
- **Calendar aliases** for friendly names
- **Attendee parsing** from iCal ATTENDEE fields

### Performance & Caching
- **Smart URL caching** with content change detection
- **Parallel URL fetching** for faster loading
- **Background auto-refresh** in interactive mode (configurable interval)
- Manual cache management (--cache-info, --clear-cache)
- Progress indicators for network operations

## Testing

Install developer dependencies by running:

```bash
pip install requirements.dev.txt
```

Then run the tests with the command:
```bash
pytest
```
