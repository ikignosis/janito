import typer
from typing import Optional, List
from pathlib import Path
from rich.console import Console
from .version import get_version

from janito.agents import AgentSingleton
from janito.config import config

from .cli.commands import handle_request, handle_ask, handle_play, handle_scan

app = typer.Typer(add_completion=False)

def typer_main(
    change_request: str = typer.Argument(None, help="Change request or command"),
    workdir: Optional[Path] = typer.Option(None, "-w", "--workdir", help="Working directory", file_okay=False, dir_okay=True),
    debug: bool = typer.Option(False, "--debug", help="Show debug information"),
    verbose: bool = typer.Option(False, "--verbose", help="Show verbose output"),
    include: Optional[List[Path]] = typer.Option(None, "-i", "--include", help="Additional paths to include"),
    ask: Optional[str] = typer.Option(None, "--ask", help="Ask a question about the codebase"),
    play: Optional[Path] = typer.Option(None, "--play", help="Replay a saved prompt file"),
    version: bool = typer.Option(False, "--version", help="Show version information"),
):
    """Janito - AI-powered code modification assistant"""
    if version:
        console = Console()
        console.print(f"Janito version {get_version()}")
        return

    workdir = workdir or Path.cwd()
    config.set_debug(debug)
    config.set_verbose(verbose)

    agent = AgentSingleton.get_agent()

    if ask:
        handle_ask(ask, workdir, include, False, agent)
    elif play:
        handle_play(play, workdir, False)
    elif change_request == "scan":
        paths_to_scan = include if include else [workdir]
        handle_scan(paths_to_scan, workdir)
    elif change_request:
        handle_request(change_request, workdir, include, False, agent)
    else:
        console = Console()
        console.print("Error: Please provide a change request or use --ask/--play options")
        raise typer.Exit(1)

def main():
    typer.run(typer_main)

if __name__ == "__main__":
    main()
