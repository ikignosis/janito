from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from pathlib import Path
from rich.console import Console
from janito.claude import ClaudeAPIAgent
from janito.prompts import build_request_analisys_prompt, SYSTEM_PROMPT
from janito.scan import collect_files_content
from janito.__main__ import handle_option_selection
from rich.panel import Panel
from rich.align import Align
from janito.common import progress_send_message
from rich.table import Table

def display_help() -> None:
    """Display available commands and their descriptions"""
    console = Console()
    
    table = Table(title="Available Commands", box=None)
    table.add_column("Command", style="cyan")
    table.add_column("Description", style="white")
    
    table.add_row(
        "ask <text>",
        "Ask a question about the codebase without making changes"
    )
    table.add_row(
        "request <text>",
        "Request code modifications or improvements"
    )
    table.add_row(
        "help",
        "Display this help message"
    )
    table.add_row(
        "exit",
        "Exit the console session"
    )
    
    console.print("\n")
    console.print(table)
    console.print("\nExamples:")
    console.print("  ask how does the error handling work?")
    console.print("  request add input validation to user functions")
    console.print("\n")

def process_command(command: str, args: str, workdir: Path, include: list[Path], claude: ClaudeAPIAgent) -> None:
    """Process console commands"""
    console = Console()
    
    if command == "help":
        display_help()
        return
        
    if command == "ask":
        if not args:
            console.print("[red]Error: Ask command requires a question[/red]")
            return
        # Get current files content
        paths_to_scan = [workdir] if workdir else []
        if include:
            paths_to_scan.extend(include)
        files_content = collect_files_content(paths_to_scan, workdir)
        
        from janito.qa import ask_question, display_answer
        answer = ask_question(args, files_content, claude)
        display_answer(answer)
        return
        
    if command == "request":
        if not args:
            console.print("[red]Error: Request command requires a description[/red]")
            return
        # Get current files content
        paths_to_scan = [workdir] if workdir else []
        if include:
            paths_to_scan.extend(include)
        files_content = collect_files_content(paths_to_scan, workdir)

        # Get initial analysis
        initial_prompt = build_request_analisys_prompt(files_content, args)
        initial_response = progress_send_message(claude, initial_prompt)

        # Show response and handle options
        console.print(initial_response)
        handle_option_selection(claude, initial_response, args, False, workdir, include)
        return
        
    console.print(f"[red]Unknown command: {command}[/red]")
    console.print("Type 'help' for available commands")

def start_console_session(workdir: Path, include: list[Path] = None) -> None:
    """Start an interactive console session using prompt_toolkit"""
    console = Console()
    claude = ClaudeAPIAgent(system_prompt=SYSTEM_PROMPT)

    # Setup prompt session with history
    history_file = workdir / '.janito' / 'console_history'
    history_file.parent.mkdir(parents=True, exist_ok=True)
    session = PromptSession(history=FileHistory(str(history_file)))

    from importlib.metadata import version
    try:
        ver = version("janito")
    except:
        ver = "dev"

    welcome_text = (
        "Welcome to Janito v" + ver + "\n"
        "Your Friendly Software Development Buddy\n\n"
        "Available commands:\n"
        "- ask <text>     Ask questions about the codebase\n"
        "- request <text> Request code modifications\n"
        "- help           Show detailed help\n"
        "- exit           Exit console"
    )
    welcome_panel = Panel(
        welcome_text,
        style="bold blue",
        border_style="bold blue"
    )
    console.print("\n")
    console.print(welcome_panel)
    console.print("\n[cyan]How can I help you with your code today?[/cyan]\n")

    while True:
        try:
            user_input = session.prompt("janito> ").strip()
            if not user_input:
                continue
                
            if user_input.lower() in ('exit', 'quit'):
                break
                
            # Split input into command and arguments
            parts = user_input.split(maxsplit=1)
            command = parts[0].lower()
            args = parts[1] if len(parts) > 1 else ""
            
            process_command(command, args, workdir, include, claude)

        except KeyboardInterrupt:
            continue
        except EOFError:
            break