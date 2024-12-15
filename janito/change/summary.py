from dataclasses import dataclass
from typing import List, Dict
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.columns import Columns
from rich.text import Text

from collections import defaultdict

@dataclass
class ChangeStats:
    """Statistics for a type of change"""
    count: int = 0
    files: List[Path] = None
    operations: Dict[str, int] = None
    
    def __post_init__(self):
        if self.files is None:
            self.files = []
        if self.operations is None:
            self.operations = defaultdict(int)

class ChangeSummary:
    """Formats and displays change statistics"""
    
    def __init__(self):
        self.stats: Dict[str, ChangeStats] = {
            'create': ChangeStats(),
            'modify': ChangeStats(),
            'remove': ChangeStats(),
            'rename': ChangeStats()
        }
        self.console = Console()

    def add_change(self, operation: str, filepath: Path):
        """Add a change to the statistics"""
        op = operation.split('_')[0]  # Extract base operation
        if op in self.stats:
            self.stats[op].count += 1
            self.stats[op].files.append(filepath)
            # Track specific operation type
            self.stats[op].operations[operation] += 1

    def display(self):
        """Display formatted change summary"""
        panels = []
        
        for op, stats in self.stats.items():
            if stats.count == 0:
                continue
                
            content = Text()
            content.append(f"{stats.count} file(s)\n\n", style="bold")
            
            # Show operation breakdown
            if stats.operations:
                content.append("Operations:\n", style="cyan")
                for op_type, count in stats.operations.items():
                    content.append(f"• {op_type}: {count}\n", style="blue")
                content.append("\n")
            
            for file in stats.files:
                content.append(f"• {file}\n", style="dim")
                
            panels.append(Panel(
                content,
                title=f"[bold]{op.title()}[/bold]",
                border_style="blue"
            ))
            
        if panels:
            self.console.print("\n[bold blue]Change Summary[/bold blue]")
            self.console.print(Columns(panels, padding=(0, 2)))
            self.console.print()