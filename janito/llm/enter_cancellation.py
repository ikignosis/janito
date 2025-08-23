"""
Enter key cancellation for LLM requests.
Allows pressing Enter to cancel ongoing requests.
"""

import threading
import sys
import time
from typing import Optional


class EnterCancellation:
    """Handles Enter key cancellation of LLM requests."""

    def __init__(self):
        self._cancel_event: Optional[threading.Event] = None
        self._listener_thread: Optional[threading.Thread] = None
        self._listening = False

    def start_monitoring(self, cancel_event: threading.Event):
        """Start monitoring for Enter key to cancel the request."""
        if self._listening:
            return

        self._cancel_event = cancel_event
        self._listening = True

        self._listener_thread = threading.Thread(
            target=self._monitor_enter_key, daemon=True
        )
        self._listener_thread.start()

    def stop_monitoring(self):
        """Stop monitoring for keyboard input."""
        self._listening = False
        if self._listener_thread and self._listener_thread.is_alive():
            self._listener_thread.join(timeout=0.1)

    def _monitor_enter_key(self):
        """Monitor for Enter key press."""
        try:
            self._handle_key_monitoring()
        except Exception:
            # Silently handle any errors
            pass

    def _handle_key_monitoring(self):
        """Handle the actual key monitoring logic."""
        import sys
        import select

        try:
            import msvcrt  # Windows-specific keyboard input

            self._monitor_windows_keys()
        except ImportError:
            self._monitor_unix_keys()

    def _monitor_windows_keys(self):
        """Monitor keys on Windows systems."""
        import msvcrt

        while (
            self._listening and self._cancel_event and not self._cancel_event.is_set()
        ):
            try:
                if msvcrt.kbhit():
                    char = msvcrt.getch()
                    if char in [b"\r", b"\n"]:
                        if self._cancel_event:
                            self._cancel_event.set()
                        break
                else:
                    time.sleep(0.05)
            except (IOError, OSError):
                break

    def _monitor_unix_keys(self):
        """Monitor keys on Unix-like systems."""
        import sys
        import select

        while (
            self._listening and self._cancel_event and not self._cancel_event.is_set()
        ):
            try:
                if sys.stdin in select.select([sys.stdin], [], [], 0.05)[0]:
                    char = sys.stdin.read(1)
                    if char in ["\r", "\n"]:
                        if self._cancel_event:
                            self._cancel_event.set()
                        break
                time.sleep(0.05)
            except:
                time.sleep(0.05)


# Global instance
_global_enter_cancellation = None


def get_enter_cancellation() -> EnterCancellation:
    """Get the global Enter cancellation instance."""
    global _global_enter_cancellation
    if _global_enter_cancellation is None:
        _global_enter_cancellation = EnterCancellation()
    return _global_enter_cancellation
