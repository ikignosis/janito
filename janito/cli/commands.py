from pathlib import Path
from typing import Optional, List
from rich.console import Console

from janito.claude import ClaudeAPIAgent
from janito.scan import preview_scan, is_dir_empty
from janito.version import get_version
from janito.config import config
from .registry import registry
from .functions import (
    process_question, replay_saved_file, ensure_workdir,
    review_text, save_to_file, collect_files_content,
    build_request_analysis_prompt, progress_send_message,
    format_analysis, handle_option_selection
)

@registry.register("version", "Show version and exit")
def handle_version():
    console = Console()
    console.print(f"Janito v{get_version()}")

@registry.register("review", "Review the provided text")
def handle_review(text: str, claude: ClaudeAPIAgent, raw: bool):
    review_text(text, claude, raw)

@registry.register("ask", "Ask a question about the codebase")
def handle_ask(question: str, workdir: Path, include: List[Path], raw: bool, claude: ClaudeAPIAgent):
    process_question(question, workdir, include, raw, claude)

@registry.register("scan", "Preview files that would be analyzed")
def handle_scan(paths_to_scan: List[Path], workdir: Path):
    preview_scan(paths_to_scan, workdir)

@registry.register("play", "Replay a saved prompt file")
def handle_play(filepath: Path, claude: ClaudeAPIAgent, workdir: Path, raw: bool):
    replay_saved_file(filepath, claude, workdir, raw)

@registry.register("request", "Process modification request")
def handle_request(request: str, workdir: Path, include: List[Path], raw: bool, claude: ClaudeAPIAgent):
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
