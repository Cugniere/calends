"""Configuration constants for the calends application."""

# Cache settings
DEFAULT_CACHE_PATH = ".calends.pkl"
DEFAULT_CACHE_EXPIRATION = 60

# Parser settings
DEFAULT_MAX_RECURRING_INSTANCES = 100
DEFAULT_EVENT_DURATION_HOURS = 1
URL_FETCH_TIMEOUT = 10

# Config file settings
DEFAULT_CONFIG_FILES = ["calendars.json", "calends.json"]
DEFAULT_CACHE_EXPIRATION_CONFIG = 60

# Interactive mode settings
DEFAULT_AUTO_REFRESH_INTERVAL = 60  # seconds, 0 to disable
