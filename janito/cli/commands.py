from pathlib import Path
from typing import Optional, List
from rich.console import Console

from janito.agents import AIAgent
from janito.scan import preview_scan, is_dir_empty, show_content_stats
from janito.config import config
from janito.change.core import process_change_request

from .functions import (
    process_question, replay_saved_file, ensure_workdir,
    read_stdin
)


def handle_ask(question: str, workdir: Path, include: List[Path], raw: bool):
    """Ask a question about the codebase"""
    workdir = ensure_workdir(workdir)
    if question == ".":
        question = read_stdin()
    process_question(question, workdir, include, raw)

def handle_scan(paths_to_scan: List[Path], workdir: Path):
    """Preview files that would be analyzed"""
    workdir = ensure_workdir(workdir)
    preview_scan(paths_to_scan, workdir)

def handle_play(filepath: Path, workdir: Path, raw: bool):
    """Replay a saved prompt file"""
    workdir = ensure_workdir(workdir)
    replay_saved_file(filepath, workdir, raw)

def handle_request(request: str, include: List[Path], raw: bool):
    """Process modification request"""
    workdir = ensure_workdir()
    console = Console()
    
    # Show empty directory message if needed
    if is_dir_empty(workdir) and not include:
        console.print("\n[bold blue]Empty directory - will create new files as needed[/bold blue]")
    
    # Process request through core function
    success, history_file = process_change_request(request)
    
    if success and history_file and config.verbose:
        try:
            rel_path = history_file.relative_to(workdir)
            console.print(f"\nChanges saved to: ./{rel_path}")
        except ValueError:
            console.print(f"\nChanges saved to: {history_file}")
    elif not success:
        console.print("[red]Failed to process change request[/red]")

