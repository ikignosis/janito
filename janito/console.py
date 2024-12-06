from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.completion import WordCompleter, PathCompleter
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.formatted_text import HTML
from pathlib import Path
from rich.console import Console
from janito.claude import ClaudeAPIAgent
from janito.prompts import build_request_analysis_prompt, SYSTEM_PROMPT
from janito.scan import collect_files_content
from janito.__main__ import handle_option_selection
from rich.panel import Panel
from rich.align import Align
from janito.common import progress_send_message
from rich.table import Table
from rich.layout import Layout
from rich.live import Live
from typing import List, Optional
import shutil

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
        "ask <text>",
        "Ask a question about the codebase without making changes"
    )
    commands_table.add_row(
        "request <text>",
        "Request code modifications or improvements"
    )
    commands_table.add_row(
        "help",
        "Display this help message"
    )
    commands_table.add_row(
        "exit",
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

def process_command(command: str, args: str, workdir: Path, include: List[Path], claude: ClaudeAPIAgent) -> None:
    """Process console commands with improved output formatting"""
    console = Console()
    
    if command == "help":
        display_help()
        return
        
    if command == "ask":
        if not args:
            console.print(Panel(
                "[red]Ask command requires a question[/red]",
                title="Error",
                border_style="red"
            ))
            return
            
        paths_to_scan = [workdir] if workdir else []
        if include:
            paths_to_scan.extend(include)
        files_content = collect_files_content(paths_to_scan, workdir)
        
        from janito.qa import ask_question, display_answer
        with console.status("[bold cyan]Processing question...[/bold cyan]"):
            answer = ask_question(args, files_content, claude)
        display_answer(answer)
        return
        
    if command == "request":
        if not args:
            console.print(Panel(
                "[red]Request command requires a description[/red]",
                title="Error",
                border_style="red"
            ))
            return
            
        paths_to_scan = [workdir] if workdir else []
        if include:
            paths_to_scan.extend(include)
        files_content = collect_files_content(paths_to_scan, workdir)

        with console.status("[bold cyan]Analyzing request...[/bold cyan]"):
            initial_prompt = build_request_analysis_prompt(files_content, args)
            initial_response = progress_send_message(claude, initial_prompt)

        console.print(initial_response)
        handle_option_selection(claude, initial_response, args, False, workdir, include)
        return
        
    console.print(Panel(
        f"[red]Unknown command: {command}[/red]\nType 'help' for available commands",
        title="Error",
        border_style="red"
    ))

def start_console_session(workdir: Path, include: Optional[List[Path]] = None) -> None:
    """Start an enhanced interactive console session"""
    console = Console()
    claude = ClaudeAPIAgent(system_prompt=SYSTEM_PROMPT)

    # Setup history with persistence
    history_file = workdir / '.janito' / 'console_history'
    history_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Create session with history and completions
    session = PromptSession(
        history=FileHistory(str(history_file)),
        completer=create_completer(workdir),
        auto_suggest=AutoSuggestFromHistory(),
        complete_while_typing=True
    )

    # Get version and terminal info
    from importlib.metadata import version
    try:
        ver = version("janito")
    except:
        ver = "dev"
    
    term_width = shutil.get_terminal_size().columns
    
    # Create welcome message
    welcome_text = (
        f"[bold blue]Welcome to Janito v{ver}[/bold blue]\n"
        "[dim]Your AI-Powered Software Development Buddy[/dim]\n\n"
        "[cyan]Features:[/cyan]\n"
        "• Command history (use ↑↓ keys)\n"
        "• Tab completion for commands\n"
        "• Auto-suggestions from history\n"
        "• Rich output formatting\n\n"
        "[cyan]Quick Start:[/cyan]\n"
        "• Type 'help' for detailed usage\n"
        "• Use 'ask' for questions\n"
        "• Use 'request' for changes\n"
        "• Press Ctrl+D to exit"
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

    while True:
        try:
            # Get input with formatted prompt
            user_input = session.prompt(
                lambda: format_prompt(workdir),
                complete_while_typing=True
            ).strip()
            
            if not user_input:
                continue
                
            if user_input.lower() in ('exit', 'quit'):
                console.print("\n[cyan]Goodbye! Have a great day![/cyan]\n")
                break
                
            # Split input into command and arguments
            parts = user_input.split(maxsplit=1)
            command = parts[0].lower()
            args = parts[1] if len(parts) > 1 else ""
            
            process_command(command, args, workdir, include, claude)

        except KeyboardInterrupt:
            continue
        except EOFError:
            console.print("\n[cyan]Goodbye! Have a great day![/cyan]\n")
            break