from typing import Optional, List
from pathlib import Path
from rich.console import Console
from rich.prompt import Prompt
from datetime import datetime, timezone

class BaseCLIHandler:
    def __init__(self):
        self.console = Console()

    def prompt_user(self, message: str, choices: List[str] = None) -> str:
        """Display a simple user prompt with optional choices"""
        if choices:
            self.console.print(f"\n[cyan]Options: {', '.join(choices)}[/cyan]")
        return Prompt.ask(f"[bold cyan]> {message}[/bold cyan]")

    def get_timestamp(self) -> str:
        """Get current UTC timestamp in YMD_HMS format"""
        return datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')

    def save_to_history(self, content: str, prefix: str) -> Path:
        """Save content to history with timestamp"""
        from janito.config import config
        history_dir = config.workspace_dir / '.janito' / 'history'
        history_dir.mkdir(parents=True, exist_ok=True)
        timestamp = self.get_timestamp()
        filename = f"{timestamp}_{prefix}.txt"
        file_path = history_dir / filename
        file_path.write_text(content)
        return file_path