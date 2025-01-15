from rich.console import Console

console = Console()

SHORTCUTS_INFO = """
Available keyboard shortcuts:
  Up/Down : Navigate command history
  Ctrl+R  : Reverse search in history
  Tab     : Auto-complete (when choices available)
  Ctrl+A  : Move cursor to start of line
  Ctrl+E  : Move cursor to end of line
  Ctrl+K  : Clear line after cursor
  Ctrl+U  : Clear line before cursor
  Ctrl+D  : Exit shell

Commands:
  /exit    : Exit the shell
  /help    : Show this help message
  /history : Show command history
  /ask     : Ask a question about the codebase
"""

def show_help():
    """Display available keyboard shortcuts and commands."""
    console.print("\n[cyan]Help Information:[/cyan]")
    console.print(SHORTCUTS_INFO)
