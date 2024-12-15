from pathlib import Path
from typing import Optional, List
from rich.console import Console

from janito.agents import AIAgent
from janito.scan import preview_scan, is_dir_empty
from janito.config import config
from janito.change.core import process_change_request, play_saved_changes
from janito.tui import TuiApp

from .functions import (
    process_question, 
    read_stdin
)

def handle_ask(question: str):
    """Ask a question about the codebase"""
    if question == ".":
        question = read_stdin()
    
    if config.tui:
        from janito.qa import ask_question
        paths_to_scan = [config.workdir] if not config.include else config.include
        from janito.scan import collect_files_content
        files_content = collect_files_content(paths_to_scan)
        answer = ask_question(question, files_content)
        app = TuiApp(answer)
        app.run()
    else:
        process_question(question)

def handle_scan(paths_to_scan: List[Path]):
    """Preview files that would be analyzed"""
    preview_scan(paths_to_scan)

def handle_play(filepath: Path):
    """Replay a saved changes or debug file"""
    play_saved_changes(filepath)

def handle_request(request: str):
    """Process modification request"""
    console = Console()
    
    is_empty = is_dir_empty(config.workdir)
    if is_empty and not config.include:
        console.print("\n[bold blue]Empty directory - will create new files as needed[/bold blue]")
    
    # Process request through core function
    success, history_file = process_change_request(request)
    
    if success and history_file and config.verbose:
        try:
            rel_path = history_file.relative_to(config.workdir)
            console.print(f"\nChanges saved to: ./{rel_path}")
        except ValueError:
            console.print(f"\nChanges saved to: {history_file}")
    elif not success:
        console.print("[red]Failed to process change request[/red]")