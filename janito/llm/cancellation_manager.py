"""
Global cancellation manager for LLM requests.
Provides a centralized way to cancel ongoing requests.
"""

import threading
from typing import Optional


class CancellationManager:
    """Manages cancellation of LLM requests across the application."""

    def __init__(self):
        self._current_cancel_event: Optional[threading.Event] = None
        self._lock = threading.Lock()
        self._keyboard_cancellation = None

    def start_new_request(self) -> threading.Event:
        """Start a new request and return its cancellation event."""
        with self._lock:
            # Create new cancellation event for this request
            self._current_cancel_event = threading.Event()

            # Start keyboard monitoring
            from janito.llm.enter_cancellation import get_enter_cancellation

            self._keyboard_cancellation = get_enter_cancellation()
            self._keyboard_cancellation.start_monitoring(self._current_cancel_event)

            return self._current_cancel_event

    def cancel_current_request(self) -> bool:
        """Cancel the current request if one is active."""
        with self._lock:
            if self._current_cancel_event is not None:
                self._current_cancel_event.set()
                return True
            return False

    def get_current_cancel_event(self) -> Optional[threading.Event]:
        """Get the current cancellation event."""
        with self._lock:
            return self._current_cancel_event

    def clear_current_request(self):
        """Clear the current request cancellation event."""
        with self._lock:
            if self._keyboard_cancellation:
                self._keyboard_cancellation.stop_monitoring()
                self._keyboard_cancellation = None
            self._current_cancel_event = None


# Global cancellation manager instance
_global_manager = None


def get_cancellation_manager() -> CancellationManager:
    """Get the global cancellation manager instance."""
    global _global_manager
    if _global_manager is None:
        _global_manager = CancellationManager()
    return _global_manager
