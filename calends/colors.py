class Colors:
    """ANSI color codes for terminal output."""
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'

    GREY = '\033[90m'
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'

    LIGHT_GREY = '\033[37m'

    @staticmethod
    def disable():
        """Disable colors (for piping or when colors not supported)."""
        for attr in dir(Colors):
            if attr.isupper():
                setattr(Colors, attr, '')
