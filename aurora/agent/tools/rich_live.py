from contextlib import contextmanager
from rich.live import Live
from rich.panel import Panel
from rich.console import Console

console = Console()

_global_live = None

@contextmanager
def global_live_panel(title="Working..."):
    global _global_live
    if _global_live is None:
        _global_live = Live(Panel("", title=title), console=console, refresh_per_second=4)
        _global_live.start()
    try:
        yield _global_live
    finally:
        pass  # Do not stop here; stopping is handled explicitly

def stop_global_live_panel():
    global _global_live
    if _global_live is not None:
        _global_live.stop()
        _global_live = None

@contextmanager
def live_panel(title="Working..."):
    global _global_live
    if _global_live is not None:
        # Update the global panel content instead of creating a nested panel
        _global_live.update(Panel("", title=title))
        yield _global_live
    else:
        # Fallback: create a temporary panel if no global panel is running
        with Live(Panel("", title=title), console=console, refresh_per_second=4) as live:
            yield live
