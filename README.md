# Calends

A minimalist terminal calendar that displays your iCal events in a clean weekly view with support for recurring events, timezones, and remote calendars.

![Demo Animation](../assets/calends.png?raw=true)

## Installation

### From Source (Development)

```bash
# Clone the repository
git clone https://github.com/cugniere/calends.git
cd calends

# Install in development mode
pip install -e .

# Or install with development dependencies
pip install -e ".[dev]"
```

### From PyPI (Coming Soon)

```bash
pip install calends
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
│ Time: Monday, October 27, 2025 at 14:00 - 15:00                              │
│ Location: Conference Room A                                                  │
│ Attendees: Alice, Bob, Charlie                                               │
│ Description: Weekly team sync to discuss project progress                    │
└──────────────────────────────────────────────────────────────────────────────┘
```

## Configuration

Calends automatically searches for configuration files in the following locations (in priority order):

1. **Current directory**: `./calendars.json` or `./calends.json`
2. **User home directory**: `~/.calends.json`
3. **User config directory**:
   - Linux/macOS: `~/.config/calends/config.json`
   - macOS (alternative): `~/Library/Application Support/calends/config.json`
   - Windows: `%APPDATA%\calends\config.json`

You can also specify a config file explicitly with `-c/--config path/to/config.json`.

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

**Example Setup:**

```bash
# Create config in user config directory (Linux/macOS)
mkdir -p ~/.config/calends
cat > ~/.config/calends/config.json << 'EOF'
{
  "calendars": {
    "Work": "https://calendar.google.com/calendar/ical/.../basic.ics",
    "Personal": "~/Documents/personal.ics"
  },
  "timezone": "LOCAL"
}
EOF

# Or create in home directory
cat > ~/.calends.json << 'EOF'
{
  "calendars": {
    "Work": "https://example.com/work.ics"
  }
}
EOF

# Then simply run calends from anywhere
calends
```

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

Install with development dependencies:

```bash
pip install -e ".[dev]"
```

Then run the tests:

```bash
pytest
```

Run tests with coverage:

```bash
pytest --cov=calends --cov-report=html
```
