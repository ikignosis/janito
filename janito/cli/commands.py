from pathlib import Path
from typing import Optional, List
from rich.console import Console

from janito.agents import AIAgent
from janito.workspace import workset  # Updated import
from janito.config import config
from janito.change.core import process_change_request
from janito.change.play import play_saved_changes
from janito.cli.history import save_to_history
from janito.agents import agent

from .handlers.ask import AskHandler
from .handlers.request import RequestHandler
from .handlers.scan import ScanHandler
from janito.change.play import play_saved_changes

def handle_ask(question: str):
    """Ask a question about the codebase"""
    handler = AskHandler()
    handler.handle(question)

def handle_scan(paths_to_scan: List[Path]):
    """Preview files that would be analyzed"""
    workset.refresh(paths_to_scan)
    workset.analyze()

def handle_play(filepath: Path):
    """Replay a saved changes or debug file"""
    play_saved_changes(filepath)

def handle_request(request: str, preview_only: bool = False):
    """Process modification request"""
    handler = RequestHandler()
    handler.handle(request, preview_only)

    # Save request and response to history
    if agent.last_response:
        save_to_history(request, agent.last_response)