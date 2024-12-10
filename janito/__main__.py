import typer
from typing import Optional, List
from pathlib import Path
from rich.console import Console
from .version import get_version

from janito.agents import agent
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
    git_commit: Optional[str] = typer.Option(None, "--git-commit", help="Do git commit with auto-generated message"),
    play: Optional[Path] = typer.Option(None, "--play", help="Replay a saved prompt file"),
    version: bool = typer.Option(False, "--version", help="Show version information"),
    save_only: bool = typer.Option(False, "--save-only", help="Only save analysis file and exit"),
    test_cmd: Optional[str] = typer.Option(None, "--test", help="Command to run tests after changes"),
    auto_apply: bool = typer.Option(False, "--auto-apply", help="Apply changes without confirmation"),
):
    """Janito - AI-powered code modification assistant"""
    if version:
        console = Console()
        console.print(f"Janito version {get_version()}")
        return

    config.set_workdir(workdir)
    config.set_debug(debug)
    config.set_verbose(verbose)

    if ask:
        handle_ask(ask, config.workdir, include, False)
    elif play:
        handle_play(play, False)
    elif change_request == "scan":
        paths_to_scan = include if include else [config.workdir]
        handle_scan(paths_to_scan)
    elif change_request:
        handle_request(change_request, include, False)

def main():
    typer.run(typer_main)

if __name__ == "__main__":
    main()
