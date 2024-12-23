from datetime import datetime
from threading import Event, Thread
from time import sleep
from rich.live import Live
from rich.text import Text

class ProgressDisplay:
    """Handles displaying progress with elapsed time while waiting for responses."""

    def __init__(self):
        self.start_time = None
        self.stop_event = Event()

    def _update_display_thread(self, live_display):
        while not self.stop_event.is_set():
            elapsed = datetime.now() - self.start_time
            live_display.update(Text.assemble(
                "Waiting for response from AI agent... (",
                (f"{elapsed.seconds}s", "magenta"),
                ")",
                justify="center"
            ))
            sleep(0.25)

    def __enter__(self):
        self.start_time = datetime.now()
        self.live = Live(Text("Waiting for response from AI agent...", justify="center"), refresh_per_second=4)
        self.live.__enter__()
        self.display_thread = Thread(target=self._update_display_thread, args=(self.live,), daemon=True)
        self.display_thread.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop_event.set()
        self.display_thread.join()
        self.live.__exit__(exc_type, exc_val, exc_tb)