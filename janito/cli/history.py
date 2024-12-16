from pathlib import Path
from datetime import datetime, timezone
from typing import List
from rich.console import Console
from rich.table import Table
from janito.config import config

def get_history_path() -> Path:
    """Get the path to the history directory"""
    history_dir = config.workdir / '.janito' / 'history'
    history_dir.mkdir(parents=True, exist_ok=True)
    return history_dir

def save_to_history(request: str, response: str) -> None:
    """Save a request and its response to the history file"""
    history_dir = get_history_path()
    timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%d_%H%M%S')
    history_file = history_dir / f"{timestamp}_request.txt"

    content = f"""Request: {request}
Timestamp: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}

Response:
{response}
"""
    history_file.write_text(content)

def display_history() -> None:
    """Display the history of requests"""
    console = Console()
    history_dir = get_history_path()

    if not history_dir.exists():
        console.print("[yellow]No history found[/yellow]")
        return

    table = Table(title="Request History")
    table.add_column("Timestamp", style="cyan")
    table.add_column("Request", style="white")
    table.add_column("File", style="dim")

    history_files = sorted(history_dir.glob("*_request.txt"), reverse=True)

    if not history_files:
        console.print("[yellow]No history found[/yellow]")
        return

    for history_file in history_files:
        try:
            content = history_file.read_text()
            request_line = next(line for line in content.splitlines() if line.startswith("Request:"))
            timestamp_line = next(line for line in content.splitlines() if line.startswith("Timestamp:"))

            request = request_line.replace("Request:", "").strip()
            timestamp = timestamp_line.replace("Timestamp:", "").strip()

            table.add_row(timestamp, request, history_file.name)
        except Exception as e:
            console.print(f"[red]Error reading {history_file}: {e}[/red]")

    console.print(table)