import shutil
import sys


def get_terminal_size():
    """
    Returns the terminal size as a tuple: (columns, rows).
    Uses Windows API via ctypes on Windows, otherwise shutil.get_terminal_size().
    """
    import os

    if os.name == "nt":
        import ctypes

        STD_OUTPUT_HANDLE = -11

        class COORD(ctypes.Structure):
            _fields_ = [("X", ctypes.c_short), ("Y", ctypes.c_short)]

        class SMALL_RECT(ctypes.Structure):
            _fields_ = [
                ("Left", ctypes.c_short),
                ("Top", ctypes.c_short),
                ("Right", ctypes.c_short),
                ("Bottom", ctypes.c_short),
            ]

        class CONSOLE_SCREEN_BUFFER_INFO(ctypes.Structure):
            _fields_ = [
                ("dwSize", COORD),
                ("dwCursorPosition", COORD),
                ("wAttributes", ctypes.c_uint16),
                ("srWindow", SMALL_RECT),
                ("dwMaximumWindowSize", COORD),
            ]

        kernel32 = ctypes.windll.kernel32
        hConsole = kernel32.GetStdHandle(STD_OUTPUT_HANDLE)
        consoleInfo = CONSOLE_SCREEN_BUFFER_INFO()
        success = kernel32.GetConsoleScreenBufferInfo(
            hConsole, ctypes.byref(consoleInfo)
        )
        if success:
            columns = consoleInfo.dwSize.X
            rows = consoleInfo.dwSize.Y
            return columns, rows
        else:
            return 80, 24
    else:
        try:
            size = shutil.get_terminal_size()
            return size.columns, size.lines
        except OSError:
            return 80, 24


def move_cursor_nth_line_from_bottom(n: int = 3):
    """
    Move the cursor to the (terminal_height - n + 1)th line (n lines from the bottom).
    """
    try:
        _, rows = shutil.get_terminal_size()

        sys.stdout.flush()
    except OSError:
        # Fallback: do nothing if terminal size can't be determined
        pass
