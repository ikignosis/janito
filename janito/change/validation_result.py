from dataclasses import dataclass, field
from typing import List, Dict, Optional
from pathlib import Path
from rich.panel import Panel
from rich.text import Text
from rich.console import Console
from rich import box

@dataclass
class SyntaxError:
    """Represents a Python syntax error with context"""
    filepath: Path
    line_number: int
    column: int
    error_message: str
    code_line: Optional[str] = None
    pointer: Optional[str] = None

    def format_error(self) -> Text:
        """Format error details with code context"""
        text = Text()
        text.append(f"📍 {self.filepath}:{self.line_number}:{self.column}\n", style="bold red")
        if self.code_line:
            text.append(f"{self.code_line}\n", style="red")
            if self.pointer:
                text.append(f"{self.pointer}\n", style="bold red")
        text.append(f"Error: {self.error_message}", style="red")
        return text

@dataclass
class ValidationResult:
    """Tracks validation results including syntax errors"""
    is_valid: bool = True
    error_message: Optional[str] = None
    syntax_errors: List[SyntaxError] = field(default_factory=list)

    def add_syntax_error(self, error: SyntaxError):
        """Add a syntax error to the collection"""
        self.syntax_errors.append(error)

    def has_syntax_errors(self) -> bool:
        """Check if there are any syntax errors"""
        return len(self.syntax_errors) > 0

    def create_error_panel(self) -> Panel:
        """Create a panel displaying all syntax errors"""
        text = Text()
        text.append("⚠️  Python Syntax Errors Detected\n\n", style="bold yellow")

        for i, error in enumerate(self.syntax_errors, 1):
            if i > 1:
                text.append("\n" + "─" * 50 + "\n\n", style="dim")
            text.append(error.format_error())

        text.append("\n\n")
        text.append("These errors will need to be fixed manually after applying changes.",
                   style="yellow")

        return Panel(
            text,
            title="[yellow]Syntax Validation Results[/yellow]",
            border_style="yellow",
            box=box.ROUNDED,
            padding=(1, 2)
        )