from pathlib import Path
from datetime import datetime, timezone
from typing import List
from rich.console import Console
from rich.table import Table

def get_history_path() -> Path:
    """Get the path to the history directory"""
    history_dir = Path.cwd() / '.janito' / 'history'
    history_dir.mkdir(parents=True, exist_ok=True)
    return history_dir

def save_to_history(request: str) -> None:
    """Save a request to the history file"""
    history_dir = get_history_path()
    timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
    history_file = history_dir / 'requests.txt'
    
    with open(history_file, 'a') as f:
        f.write(f"{timestamp}: {request}\n")

def display_history() -> None:
    """Display the history of requests"""
    console = Console()
    history_file = get_history_path() / 'requests.txt'
    
    if not history_file.exists():
        console.print("[yellow]No history found[/yellow]")
        return
    
    table = Table(title="Request History")
    table.add_column("Timestamp", style="cyan")
    table.add_column("Request", style="white")
    
    with open(history_file) as f:
        for line in f:
            timestamp, request = line.strip().split(': ', 1)
            table.add_row(timestamp, request)
    
    console.print(table)