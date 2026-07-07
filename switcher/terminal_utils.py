import sys
import termios
from typing import Tuple, Optional


def clear_and_print(text: str, newline: bool = False, width: int = 80) -> None:
    """Clear the current terminal line and print text cleanly.

    If newline is False the function updates the status line in-place
    (no trailing newline). If newline is True it prints the message and
    moves to the next line.
    """
    try:
        # Overwrite current line with spaces then return to line start
        sys.stdout.write("\r" + " " * width + "\r")
        sys.stdout.write(text)
        if newline:
            sys.stdout.write("\n")
        sys.stdout.flush()
    except Exception:
        # Fallback to a simple print if stdout isn't a TTY or writing fails
        if newline:
            print(text, flush=True)
        else:
            print(text, end="", flush=True)


def disable_echo() -> Tuple[Optional[int], Optional[list]]:
    """Disable local terminal echo and return (fd, orig_attrs).

    Returns (None, None) if stdin is not a TTY or changing attributes failed.
    """
    try:
        if hasattr(sys.stdin, "fileno") and sys.stdin.isatty():
            fd = sys.stdin.fileno()
            orig_attrs = termios.tcgetattr(fd)
            new_attrs = list(orig_attrs)
            # lflag is index 3
            new_attrs[3] = new_attrs[3] & ~termios.ECHO
            termios.tcsetattr(fd, termios.TCSADRAIN, new_attrs)
            return fd, orig_attrs
    except Exception:
        pass
    return None, None


def restore_terminal(fd: Optional[int], orig_attrs: Optional[list]) -> None:
    """Restore terminal attributes previously returned by disable_echo.

    No-op if fd or orig_attrs are None.
    """
    try:
        if fd is not None and orig_attrs is not None:
            termios.tcsetattr(fd, termios.TCSADRAIN, orig_attrs)
    except Exception:
        pass


def flush_input() -> None:
    """Flush any pending input on stdin (if a TTY)."""
    try:
        if hasattr(sys.stdin, "fileno") and sys.stdin.isatty():
            termios.tcflush(sys.stdin, termios.TCIFLUSH)
    except Exception:
        pass
