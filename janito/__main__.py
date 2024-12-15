import typer
from typing import Optional, List
from pathlib import Path
from rich.console import Console
from rich.text import Text
from .version import get_version

from janito.agents import agent
from janito.config import config

from .cli.commands import handle_request, handle_ask, handle_play, handle_scan
from .cli.input import read_input

app = typer.Typer(add_completion=False)

def typer_main(
    change_request: str = typer.Argument(None, help="Change request or command"),
    workdir: Optional[Path] = typer.Option(None, "-w", "--workdir", help="Working directory", file_okay=False, dir_okay=True),
    debug: bool = typer.Option(False, "--debug", help="Show debug information"),
    verbose: bool = typer.Option(False, "--verbose", help="Show verbose output"),
    include: Optional[List[Path]] = typer.Option(None, "-i", "--include", help="Additional paths to include"),
    ask: Optional[str] = typer.Option(None, "--ask", help="Ask a question about the codebase"),
    play: Optional[Path] = typer.Option(None, "--play", help="Replay a saved prompt file"),
    scan: bool = typer.Option(False, "--scan", help="Preview files that would be analyzed"),
    version: bool = typer.Option(False, "--version", help="Show version information"),
    test_cmd: Optional[str] = typer.Option(None, "--test", help="Command to run tests after changes"),
    auto_apply: bool = typer.Option(False, "--auto-apply", help="Apply changes without confirmation"),
    tui: bool = typer.Option(False, "--tui", help="Use terminal user interface"),
    input_mode: bool = typer.Option(False, "--input", help="Read request from stdin"),
    history: bool = typer.Option(False, "--history", help="Display history of requests"),
    recursive: bool = typer.Option(False, "-r", "--recursive", help="Scan directories recursively"),
):
    """Janito - AI-powered code modification assistant"""
    if version:
        console = Console()
        console.print(f"Janito version {get_version()}")
        return

    if history:
        from janito.cli.history import display_history
        display_history()
        return

    config.set_workdir(workdir)
    config.set_debug(debug)
    config.set_verbose(verbose)
    config.set_auto_apply(auto_apply)
    config.set_include(include)
    config.set_tui(tui)
    config.set_recursive(recursive)

    if ask:
        handle_ask(ask)
    elif play:
        handle_play(play)
    elif scan:
        paths_to_scan = include or [config.workdir]
        handle_scan(paths_to_scan)
    elif input_mode:
        request = read_input()
        if request:
            handle_request(request)
        else:
            console = Console()
            console.print("[red]No input provided[/red]")
    elif change_request:
        handle_request(change_request)
    else:
        console = Console()
        error_text = Text("No command given", style="red")
        usage_hint = Text("\nUsage: janito <change-request> [OPTIONS]", style="yellow")
        console.print(error_text)
        console.print(usage_hint)

def main():
    typer.run(typer_main)

if __name__ == "__main__":
    main()