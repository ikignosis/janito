from pathlib import Path
from typing import Optional, List
from rich.console import Console

from janito.agents import AIAgent
from janito.scan import preview_scan, is_dir_empty
from janito.config import config

from .functions import (
    process_question, replay_saved_file, ensure_workdir,
    review_text, save_to_file, collect_files_content,
    build_request_analysis_prompt, progress_send_message,
    format_analysis, handle_option_selection, read_stdin
)


def handle_ask(question: str, workdir: Path, include: List[Path], raw: bool, agent: AIAgent):
    """Ask a question about the codebase"""
    workdir = ensure_workdir(workdir)
    if question == ".":
        question = read_stdin()
    process_question(question, workdir, include, raw, agent)

def handle_scan(paths_to_scan: List[Path], workdir: Path):
    """Preview files that would be analyzed"""
    workdir = ensure_workdir(workdir)
    preview_scan(paths_to_scan, workdir)

def handle_play(filepath: Path, workdir: Path, raw: bool):
    """Replay a saved prompt file"""
    workdir = ensure_workdir(workdir)
    replay_saved_file(filepath, workdir, raw)

def handle_request(request: str, workdir: Path, include: List[Path], raw: bool, agent: AIAgent):
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
    initial_response = progress_send_message(initial_prompt)
    save_to_file(initial_response, 'analysis', workdir)
    
    format_analysis(initial_response, raw, agent)
    
    handle_option_selection(initial_response, request, raw, workdir, include)
