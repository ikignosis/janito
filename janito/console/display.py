from pathlib import Path
import shutil
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.formatted_text import HTML
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.layout import Layout
from importlib.metadata import version

def create_completer(workdir: Path) -> WordCompleter:
    """Create command completer with common commands and paths"""
    commands = [
        'ask', 'request', 'help', 'exit', 'quit',
        '--raw', '--verbose', '--debug', '--test'
    ]
    return WordCompleter(commands, ignore_case=True)

def format_prompt(workdir: Path) -> HTML:
    """Format the prompt with current directory"""
    cwd = workdir.name
    return HTML(f'<ansigreen>janito</ansigreen> <ansiblue>{cwd}</ansiblue>> ')

def display_help() -> None:
    """Display available commands, options and their descriptions"""
    console = Console()
    
    layout = Layout()
    layout.split_column(
        Layout(name="header"),
        Layout(name="commands"),
        Layout(name="options"),
        Layout(name="examples")
    )
    
    # Header
    header_table = Table(box=None, show_header=False)
    header_table.add_row("[bold cyan]Janito Console Help[/bold cyan]")
    header_table.add_row("[dim]Your AI-powered software development buddy[/dim]")
    
    # Commands table
    commands_table = Table(title="Available Commands", box=None)
    commands_table.add_column("Command", style="cyan", width=20)
    commands_table.add_column("Description", style="white")
    
    commands_table.add_row(
        "/ask <text> (/a)",
        "Ask a question about the codebase without making changes"
    )
    commands_table.add_row(
        "<text> or /request <text> (/r)",
        "Request code modifications or improvements"
    )
    commands_table.add_row(
        "/help (/h)",
        "Display this help message"
    )
    commands_table.add_row(
        "/quit or /exit (/q)",
        "Exit the console session"
    )

    # Options table
    options_table = Table(title="Common Options", box=None)
    options_table.add_column("Option", style="cyan", width=20)
    options_table.add_column("Description", style="white")

    options_table.add_row(
        "--raw",
        "Display raw response without formatting"
    )
    options_table.add_row(
        "--verbose",
        "Show additional information during execution"
    )
    options_table.add_row(
        "--debug",
        "Display detailed debug information"
    )
    options_table.add_row(
        "--test <cmd>",
        "Run specified test command before applying changes"
    )
    
    # Examples panel
    examples = Panel(
        "\n".join([
            "[dim]Basic Commands:[/dim]",
            "  ask how does the error handling work?",
            "  request add input validation to user functions",
            "",
            "[dim]Using Options:[/dim]",
            "  request update tests --verbose",
            "  ask explain auth flow --raw",
            "  request optimize code --test 'pytest'",
            "",
            "[dim]Complex Examples:[/dim]",
            "  request refactor login function --verbose --test 'python -m unittest'",
            "  ask code structure --raw --debug"
        ]),
        title="Examples",
        border_style="blue"
    )
    
    # Update layout
    layout["header"].update(header_table)
    layout["commands"].update(commands_table)
    layout["options"].update(options_table)
    layout["examples"].update(examples)
    
    console.print(layout)

def display_welcome(workdir: Path) -> None:
    """Display welcome message and console information"""
    console = Console()
    try:
        ver = version("janito")
    except:
        ver = "dev"
    
    term_width = shutil.get_terminal_size().columns

    COLORS = {
        'primary': '#729FCF',    # Soft blue for primary elements
        'secondary': '#8AE234',  # Bright green for actions/success
        'accent': '#AD7FA8',     # Purple for accents
        'muted': '#7F9F7F',      # Muted green for less important text
    }
    
    welcome_text = (
        f"[bold {COLORS['primary']}]Welcome to Janito v{ver}[/bold {COLORS['primary']}]\n"
        f"[{COLORS['muted']}]Your AI-Powered Software Development Buddy[/{COLORS['muted']}]\n\n"
        f"[{COLORS['accent']}]Keyboard Shortcuts:[/{COLORS['accent']}]\n"
        "• ↑↓ : Navigate command history\n"
        "• Tab : Complete commands and paths\n"
        "• Ctrl+D : Exit console\n"
        "• Ctrl+C : Cancel current operation\n\n"
        f"[{COLORS['accent']}]Available Commands:[/{COLORS['accent']}]\n"
        "• /ask (or /a) : Ask questions about code\n"
        "• /request (or /r) : Request code changes\n"
        "• /help (or /h) : Show detailed help\n"
        "• /quit (or /q) : Exit console\n\n"
        f"[{COLORS['secondary']}]Current Version:[/{COLORS['secondary']}] v{ver}\n"
        f"[{COLORS['muted']}]Working Directory:[/{COLORS['muted']}] {workdir.absolute()}"
    )
    
    welcome_panel = Panel(
        welcome_text,
        width=min(80, term_width - 4),
        border_style="blue",
        title="Janito Console",
        subtitle="Press Tab for completions"
    )
    
    console.print("\n")
    console.print(welcome_panel)
    console.print("\n[cyan]How can I help you with your code today?[/cyan]\n")
