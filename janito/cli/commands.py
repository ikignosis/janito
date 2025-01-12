from pathlib import Path
from rich.console import Console
from janito.agents import agent
from janito.shell.user_prompt import prompt_user

from janito.workspace import workset
from janito.config import config
from janito.change.core import process_change_request
from janito.change.play import play_saved_changes
from janito.cli.history import save_to_history
from janito.qa import ask_question, display_answer

console = Console()

def handle_ask(question: str):
    """Process a question about the codebase"""
    answer = ask_question(question)

    display_answer(answer)

def handle_scan():
    """Preview files that would be analyzed"""
    workset.show()

def handle_play(filepath: Path):
    """Replay a saved changes or debug file"""
    play_saved_changes(filepath)

def is_dir_empty(path: Path) -> bool:
    """Check if directory is empty or only contains empty directories."""
    if not path.is_dir():
        return False

    for item in path.iterdir():
        if item.name.startswith(('.', '__pycache__')):
            continue
        if item.is_file():
            return False
        if item.is_dir() and not is_dir_empty(item):
            return False
    return True

def handle_request(request: str = None, preview_only: bool = False, single: bool = False):
    """Process modification request"""
    if not request:
        return

    is_empty = is_dir_empty(config.workspace_dir)
    if is_empty and not config.include:
        console.print("\n[bold blue]Empty directory - will create new files as needed[/bold blue]")

    success, history_file = process_change_request(request, preview_only, single=single)

    if success and history_file and config.verbose:
        try:
            rel_path = history_file.relative_to(config.workspace_dir)
            console.print(f"\nChanges saved to: ./{rel_path}")
        except ValueError:
            console.print(f"\nChanges saved to: {history_file}")
    elif not success:
        console.print("[red]Failed to process change request[/red]")

    # Save request and response to history
    if agent.last_response:
        save_to_history(request, agent.last_response)
