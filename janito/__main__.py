import typer
from typing import Optional, List, Set
from pathlib import Path
from rich.text import Text
from rich import print as rich_print
from rich.console import Console
from rich.text import Text
from .version import get_version

from janito.agents import agent
from janito.config import config
from janito.workspace import workspace, workset
from .cli.commands import handle_request, handle_ask, handle_play, handle_scan

app = typer.Typer(add_completion=False)

def validate_paths(paths: Optional[List[Path]]) -> Optional[List[Path]]:
    """Validate include paths for duplicates.
    
    Args:
        paths: List of paths to validate, or None if no paths provided
        
    Returns:
        Validated list of paths or None if no paths provided
    """
    if not paths:  # This handles both None and empty list cases
        return None

    # Convert paths to absolute and resolve symlinks
    resolved_paths: Set[Path] = set()
    unique_paths: List[Path] = []

    for path in paths:
        resolved = path.absolute().resolve()
        if resolved in resolved_paths:
            error_text = Text(f"\nError: Duplicate path provided: {path} ", style="red")
            rich_print(error_text)
            raise typer.Exit(1)
        resolved_paths.add(resolved)
        unique_paths.append(path)

    return unique_paths if unique_paths else None

def typer_main(
    change_request: str = typer.Argument(None, help="Change request or command"),
    workspace_dir: Optional[Path] = typer.Option(None, "-w", "--workspace_dir", help="Working directory", file_okay=False, dir_okay=True),
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
    history: bool = typer.Option(False, "--history", help="Display history of requests"),
    recursive: Optional[List[Path]] = typer.Option(None, "-r", "--recursive", help="Paths to scan recursively (directories only)"),
    demo: bool = typer.Option(False, "--demo", help="Run demo scenarios"),
    skip_work: bool = typer.Option(False, "--skip-work", help="Skip scanning workspace_dir when using include paths"),
):
    """Janito - AI-powered code modification assistant"""
    if version:
        console = Console()
        console.print(f"Janito version {get_version()}")
        return

    if demo:
        from janito.cli.handlers.demo import DemoHandler
        handler = DemoHandler()
        handler.handle()
        return

    if history:
        from janito.cli.history import display_history
        display_history()
        return

    # Configure workspace
    config.set_workspace_dir(workspace_dir)
    config.set_debug(debug)
    config.set_verbose(verbose)
    config.set_auto_apply(auto_apply)
    config.set_tui(tui)

    # Configure workset
    workset.skip_workspace(skip_work)
    if include:
        resolved_paths = []
        for path in include:
            path = config.workspace_dir / path
            resolved_paths.append(path.resolve())
        workset.include(resolved_paths)

    # Validate recursive paths
    if recursive:
        resolved_paths = []
        for path in recursive:
            final_path = config.workspace_dir / path
            if not path.is_dir():
                error_text = Text(f"\nError: Recursive path must be a directory: {path} ", style="red")
                rich_print(error_text)
                raise typer.Exit(1)
            resolved_paths.append(final_path.resolve())
        workset.recursive(resolved_paths)
        # Add recursive paths to include paths
        all_paths = list(workset.paths) + resolved_paths
        workset.include(all_paths)

    # Validate skip_work usage
    if skip_work and not workset.paths:
        error_text = Text("\nError: --skip-work requires at least one include path (-i or -r)", style="red")
        rich_print(error_text)
        raise typer.Exit(1)

    if test_cmd:
        config.set_test_cmd(test_cmd)

    # Refresh workset content before handling commands
    workset.refresh()

    if ask:
        handle_ask(ask)
    elif play:
        handle_play(play)
    elif scan:
        handle_scan(workset.get_scan_paths())
    elif change_request:
        handle_request(change_request)
    else:
        from janito.shell import start_shell
        start_shell()

def main():
    typer.run(typer_main)

if __name__ == "__main__":
    main()