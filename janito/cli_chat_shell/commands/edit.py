import os
import webbrowser
from janito.agent.runtime_config import runtime_config


def handle_edit(console, args=None, shell_state=None, **kwargs):
    if not args or len(args) < 1:
        console.print("[red]Usage: /edit <filename>[/red]")
        return
    filename = args[0]
    if not os.path.isfile(filename):
        console.print(f"[red]File not found:[/red] {filename}")
        return
    port = getattr(shell_state, "termweb_port", None) or runtime_config.get(
        "termweb_port", 8080
    )
    url = f"http://localhost:{port}/?path={filename}"
    console.print(
        f"[green]Opening in browser:[/green] [underline blue]{url}[/underline blue]"
    )
    webbrowser.open(url)
