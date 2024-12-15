from pathlib import Path
from rich.console import Console
from janito.config import config
from janito.scan import is_dir_empty
from janito.change.core import process_change_request
from ..base import BaseCLIHandler

class RequestHandler(BaseCLIHandler):
    def handle(self, request: str, preview_only: bool = False):
        """Process a modification request"""
        is_empty = is_dir_empty(config.workdir)
        if is_empty and not config.include:
            self.console.print("\n[bold blue]Empty directory - will create new files as needed[/bold blue]")

        success, history_file = process_change_request(request, preview_only)

        if success and history_file and config.verbose:
            try:
                rel_path = history_file.relative_to(config.workdir)
                self.console.print(f"\nChanges saved to: ./{rel_path}")
            except ValueError:
                self.console.print(f"\nChanges saved to: {history_file}")
        elif not success:
            self.console.print("[red]Failed to process change request[/red]")