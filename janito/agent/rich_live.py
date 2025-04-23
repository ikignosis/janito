from rich.live import Live
from rich.markdown import Markdown
from rich.console import Console


class LiveMarkdownDisplay:
    def __init__(self, console=None):
        self.console = console or Console()
        self._accumulated = ""
        self._live = None

    def start(self):
        self._live = Live(
            Markdown(self._accumulated), console=self.console, refresh_per_second=8
        )
        self._live.__enter__()

    def update(self, part):
        self._accumulated += part
        # Only re-render on newlines for efficiency
        if "\n" in part:
            self._live.update(Markdown(self._accumulated))

    def stop(self):
        if self._live:
            self._live.__exit__(None, None, None)
            self._live = None

    def reset(self):
        self._accumulated = ""
        if self._live:
            self._live.update(Markdown(self._accumulated))
