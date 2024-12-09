from pathlib import Path
from typing import Optional, List
from rich.console import Console

from janito.claude import ClaudeAPIAgent
from janito.scan import preview_scan, is_dir_empty
from janito.config import config

from .functions import (
    process_question, replay_saved_file, ensure_workdir,
    review_text, save_to_file, collect_files_content,
    build_request_analysis_prompt, progress_send_message,
    format_analysis, handle_option_selection
)

def handle_version():
    """Show version and exit"""
    console = Console()
    console.print(f"Janito v{get_version()}")

def handle_review(text: str, claude: ClaudeAPIAgent, raw: bool):
    """Review the provided text"""
    review_text(text, claude, raw)

def handle_ask(question: str, workdir: Path, include: List[Path], raw: bool, claude: ClaudeAPIAgent):
    """Ask a question about the codebase"""
    workdir = ensure_workdir(workdir)
    process_question(question, workdir, include, raw, claude)

def handle_scan(paths_to_scan: List[Path], workdir: Path):
    """Preview files that would be analyzed"""
    workdir = ensure_workdir(workdir)
    preview_scan(paths_to_scan, workdir)

def handle_play(filepath: Path, claude: ClaudeAPIAgent, workdir: Path, raw: bool):
    """Replay a saved prompt file"""
    workdir = ensure_workdir(workdir)
    replay_saved_file(filepath, claude, workdir, raw)

def handle_request(request: str, workdir: Path, include: List[Path], raw: bool, claude: ClaudeAPIAgent):
    """Process modification request"""
    workdir = ensure_workdir(workdir)
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
