import typer
from typing import Optional, List
from pathlib import Path
from janito.claude import ClaudeAPIAgent
from janito.prompts import SYSTEM_PROMPT
from janito.config import config
from janito.version import get_version
from janito.scan import preview_scan, is_dir_empty
from rich.console import Console

from .cli.functions import (
    process_question,
    replay_saved_file, 
    ensure_workdir,
    review_text,
    save_to_file,
    collect_files_content,
    build_request_analysis_prompt,
    progress_send_message,
    format_analysis,
    handle_option_selection
)

def typer_main(
    request: Optional[str] = typer.Argument(None, help="The modification request"),
    ask: Optional[str] = typer.Option(None, "--ask", help="Ask a question about the codebase"),
    review: Optional[str] = typer.Option(None, "--review", help="Review the provided text"),
    workdir: Optional[Path] = typer.Option(None, "-w", "--workdir", 
                                         help="Working directory (defaults to current directory)", 
                                         file_okay=False, dir_okay=True),
    raw: bool = typer.Option(False, "--raw", help="Print raw response instead of markdown format"),
    play: Optional[Path] = typer.Option(None, "--play", help="Replay a saved prompt file"),
    include: Optional[List[Path]] = typer.Option(None, "-i", "--include", help="Additional paths to include in analysis", exists=True),
    debug: bool = typer.Option(False, "--debug", help="Show debug information"),
    verbose: bool = typer.Option(False, "-v", "--verbose", help="Show verbose output"),
    scan: bool = typer.Option(False, "--scan", help="Preview files that would be analyzed"),
    version: bool = typer.Option(False, "--version", help="Show version and exit"),
    test: Optional[str] = typer.Option(None, "-t", "--test", help="Test command to run before applying changes"),
) -> None:
    """
    Analyze files and provide modification instructions.
    """

    if version:
        console = Console()
        console.print(f"Janito v{get_version()}")
        raise typer.Exit()

    config.set_debug(debug)
    config.set_verbose(verbose)
    config.set_test_cmd(test)

    claude = ClaudeAPIAgent(system_prompt=SYSTEM_PROMPT)

    if review:
        review_text(review, claude, raw)
        return

    if not any([request, ask, play, scan]):
        workdir = workdir or Path.cwd()
        workdir = ensure_workdir(workdir)
        from janito.console import start_console_session
        start_console_session(workdir, include)
        return

    workdir = workdir or Path.cwd()
    workdir = ensure_workdir(workdir)
    
    if include:
        include = [
            path if path.is_absolute() else (workdir / path).resolve()
            for path in include
        ]
    
    if ask:
        process_question(ask, workdir, include, raw, claude)
        return

    if scan:
        paths_to_scan = include if include else [workdir]
        preview_scan(paths_to_scan, workdir)
        return

    if play:
        replay_saved_file(play, claude, workdir, raw)
        return

    paths_to_scan = include if include else [workdir]
    
    is_empty = is_dir_empty(workdir)
    if is_empty and not include:
        console = Console()
        console.print("\n[bold blue]Empty directory - will create new files as needed[/bold blue]")
        files_content = ""
    else:
        files_content = collect_files_content(paths_to_scan, workdir)
    
    initial_prompt = build_request_analysis_prompt(files_content, request)
    initial_response = progress_send_message(claude, initial_prompt)
    save_to_file(initial_response, 'analysis', workdir)
    
    format_analysis(initial_response, raw, claude)
    
    handle_option_selection(claude, initial_response, request, raw, workdir, include)

def main():
    typer.run(typer_main)

if __name__ == "__main__":
    main()