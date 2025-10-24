"""Interactive navigation for calendar views."""

import sys
import tty
import termios
from typing import Optional


class KeyboardInput:
    """Handle keyboard input for interactive navigation."""

    @staticmethod
    def get_key() -> Optional[str]:
        """
        Get a single keypress from the user.

        Returns:
            The key pressed, or None if input is unavailable
        """
        if not sys.stdin.isatty():
            return None

        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ch = sys.stdin.read(1)

            if ch == '\x1b':
                ch2 = sys.stdin.read(1)
                if ch2 == '[':
                    ch3 = sys.stdin.read(1)
                    if ch3 == 'A':
                        return 'UP'
                    elif ch3 == 'B':
                        return 'DOWN'
                    elif ch3 == 'C':
                        return 'RIGHT'
                    elif ch3 == 'D':
                        return 'LEFT'
                return 'ESC'
            elif ch == '\r' or ch == '\n':
                return 'ENTER'
            elif ch == '\x03':
                return 'CTRL_C'
            elif ch == '\x04':
                return 'CTRL_D'
            else:
                return ch
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

    @staticmethod
    def clear_screen() -> None:
        """Clear the terminal screen."""
        print('\033[2J\033[H', end='', flush=True)

    @staticmethod
    def show_help() -> None:
        """Display help for interactive navigation."""
        from .colors import Colors
        print(f"\n{Colors.BOLD}Interactive Navigation Help:{Colors.RESET}")
        print(f"{Colors.CYAN}  n, →, SPACE{Colors.RESET}  Next week")
        print(f"{Colors.CYAN}  p, ←{Colors.RESET}         Previous week")
        print(f"{Colors.CYAN}  t{Colors.RESET}            Today (current week)")
        print(f"{Colors.CYAN}  j{Colors.RESET}            Jump to specific date")
        print(f"{Colors.CYAN}  h, ?{Colors.RESET}         Show this help")
        print(f"{Colors.CYAN}  q, ESC{Colors.RESET}       Quit")
        print(f"\n{Colors.DIM}Press any key to continue...{Colors.RESET}", flush=True)
