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

from .handlers.ask import AskHandler
from .handlers.request import RequestHandler
from .handlers.scan import ScanHandler
from janito.change.core import play_saved_changes

def handle_ask(question: str):
    """Ask a question about the codebase"""
    handler = AskHandler()
    handler.handle(question)

def handle_scan(paths_to_scan: List[Path]):
    """Preview files that would be analyzed"""
    handler = ScanHandler()
    handler.handle(paths_to_scan)

def handle_play(filepath: Path):
    """Replay a saved changes or debug file"""
    play_saved_changes(filepath)

def handle_request(request: str, preview_only: bool = False):
    """Process modification request"""
    handler = RequestHandler()
    handler.handle(request, preview_only)