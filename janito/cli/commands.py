from pathlib import Path
from typing import Optional, List
from rich.console import Console

from janito.agents import AIAgent
from janito.scan import preview_scan, is_dir_empty, show_content_stats
from janito.config import config
from janito.git.commit import git_commit

from .functions import (
    process_question, replay_saved_file, ensure_workdir,
    review_text, save_to_file, collect_files_content,
    build_request_analysis_prompt, progress_send_message,
    format_analysis, handle_option_selection, read_stdin, preview_and_apply_changes
)


def handle_ask(question: str, include: List[Path], raw: bool):
    """Ask a question about the codebase"""
    workdir = ensure_workdir()
    if question == ".":
        question = read_stdin()
    process_question(question, include, raw)

def handle_scan(paths_to_scan: List[Path]):
    """Preview files that would be analyzed"""
    workdir = ensure_workdir()
    preview_scan(paths_to_scan)

def handle_play(filepath: Path, raw: bool):
    """Replay a saved prompt file"""
    workdir = ensure_workdir()
    replay_saved_file(filepath, raw)

def handle_request(request: str, include: List[Path], raw: bool, save_only: bool = False):
    """Process modification request"""
    workdir = ensure_workdir()
    paths_to_scan = include if include else [workdir]
    
    is_empty = is_dir_empty(workdir)
    if is_empty and not include:
        console = Console()
        console.print("\n[bold blue]Empty directory - will create new files as needed[/bold blue]")
        files_content = ""
    else:
        files_content = collect_files_content(paths_to_scan)
        show_content_stats(files_content)
    
    initial_prompt = build_request_analysis_prompt(files_content, request)
    initial_response = progress_send_message(initial_prompt)
    save_to_file(initial_response, 'analysis')
            
    format_analysis(initial_response, raw)
    
    changes = handle_option_selection(initial_response, request, raw, include)
    preview_and_apply_changes(changes, config.test_cmd, save_only)
    
def handle_git_commit():
    git_commit()