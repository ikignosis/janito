import typer
from typing import Optional, Dict, Any, List
from pathlib import Path
from janito.claude import ClaudeAPIAgent
import shutil
from janito.prompts import (
    build_selected_option_prompt,
    SYSTEM_PROMPT,    
)
from rich.console import Console
from rich.markdown import Markdown
import re
import tempfile
import json
from rich.syntax import Syntax
from janito.contentchange import (
    handle_changes_file, 
    get_file_type,
    parse_block_changes,
    preview_and_apply_changes,
    format_parsed_changes,
)
from rich.table import Table
from rich.columns import Columns
from rich.panel import Panel
from rich.text import Text
from rich.rule import Rule
from rich import box
from datetime import datetime, timezone
from itertools import chain
from janito.scan import collect_files_content, is_dir_empty, preview_scan
from janito.qa import ask_question, display_answer
from rich.prompt import Prompt, Confirm
from janito.config import config
from janito.version import get_version
from janito.common import progress_send_message
from janito.analysis import format_analysis, build_request_analysis_prompt, parse_analysis_options, get_history_file_type

def prompt_user(message: str, choices: List[str] = None) -> str:
    """Display a prominent user prompt with optional choices"""
    console = Console()
    console.print()
    console.print(Rule(" User Input Required ", style="bold cyan"))
    
    if choices:
        choice_text = f"[cyan]Options: {', '.join(choices)}[/cyan]"
        console.print(Panel(choice_text, box=box.ROUNDED))
    
    return Prompt.ask(f"[bold cyan]> {message}[/bold cyan]")

def validate_option_letter(letter: str, options: dict) -> bool:
    """Validate if the given letter is a valid option or 'M' for modify"""
    return letter.upper() in options or letter.upper() == 'M'

def get_option_selection() -> str:
    """Get user input for option selection with modify option"""
    console = Console()
    console.print("\n[cyan]Enter option letter or 'M' to modify request[/cyan]")
    while True:
        letter = prompt_user("Select option").strip().upper()
        if letter == 'M' or (letter.isalpha() and len(letter) == 1):
            return letter
        console.print("[red]Please enter a valid letter or 'M'[/red]")

def get_changes_history_path(workdir: Path) -> Path:
    """Create and return the changes history directory path"""
    changes_history_dir = workdir / '.janito' / 'changes_history'
    changes_history_dir.mkdir(parents=True, exist_ok=True)
    return changes_history_dir

def get_timestamp() -> str:
    """Get current UTC timestamp in YMD_HMS format with leading zeros"""
    return datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')

def save_prompt_to_file(prompt: str) -> Path:
    """Save prompt to a named temporary file that won't be deleted"""
    temp_file = tempfile.NamedTemporaryFile(prefix='selected_', suffix='.txt', delete=False)
    temp_path = Path(temp_file.name)
    temp_path.write_text(prompt)
    return temp_path

def save_to_file(content: str, prefix: str, workdir: Path) -> Path:
    """Save content to a timestamped file in changes history directory"""
    changes_history_dir = get_changes_history_path(workdir)
    timestamp = get_timestamp()
    filename = f"{timestamp}_{prefix}.txt"
    file_path = changes_history_dir / filename
    file_path.write_text(content)
    return file_path

def modify_request(request: str) -> str:
    """Display current request and get modified version with improved formatting"""
    console = Console()
    
    # Display current request in a panel with clear formatting
    console.print("\n[bold cyan]Current Request:[/bold cyan]")
    console.print(Panel(
        Text(request, style="white"),
        border_style="blue",
        title="Previous Request",
        padding=(1, 2)
    ))
    
    # Get modified request with clear prompt
    console.print("\n[bold cyan]Enter modified request below:[/bold cyan]")
    console.print("[dim](Press Enter to submit, Ctrl+C to cancel)[/dim]")
    try:
        new_request = prompt_user("Modified request")
        if not new_request.strip():
            console.print("[yellow]No changes made, keeping original request[/yellow]")
            return request
        return new_request
    except KeyboardInterrupt:
        console.print("\n[yellow]Modification cancelled, keeping original request[/yellow]")
        return request

def handle_option_selection(claude: ClaudeAPIAgent, initial_response: str, request: str, raw: bool = False, workdir: Optional[Path] = None, include: Optional[List[Path]] = None) -> None:
    """Handle option selection and implementation details"""
    options = parse_analysis_options(initial_response)
    if not options:
        console = Console()
        console.print("[red]No valid options found in the response[/red]")
        return

    while True:
        option = get_option_selection()
        
        if option == 'M':
            # Use the new modify_request function for better UX
            new_request = modify_request(request)
            if new_request == request:
                continue
                
            # Rerun analysis with new request
            paths_to_scan = [workdir] if workdir else []
            if include:
                paths_to_scan.extend(include)
            files_content = collect_files_content(paths_to_scan, workdir) if paths_to_scan else ""
            
            initial_prompt = build_request_analysis_prompt(files_content, new_request)
            initial_response = progress_send_message(claude, initial_prompt)
            save_to_file(initial_response, 'analysis', workdir)
            
            format_analysis(initial_response, raw, claude)
            options = parse_analysis_options(initial_response)
            if not options:
                console = Console()
                console.print("[red]No valid options found in the response[/red]")
                return
            continue
            
        if not validate_option_letter(option, options):
            console = Console()
            console.print(f"[red]Invalid option '{option}'. Valid options are: {', '.join(options.keys())} or 'M' to modify[/red]")
            continue
            
        break

    paths_to_scan = [workdir] if workdir else []
    if include:
        paths_to_scan.extend(include)
    files_content = collect_files_content(paths_to_scan, workdir) if paths_to_scan else ""
    
    selected_prompt = build_selected_option_prompt(option, request, initial_response, files_content)
    prompt_file = save_to_file(selected_prompt, 'selected', workdir)
    if config.verbose:
        print(f"\nSelected prompt saved to: {prompt_file}")
    
    selected_response = progress_send_message(claude, selected_prompt)
    
    changes_file = save_to_file(selected_response, 'changes', workdir)
    if config.verbose:
        print(f"\nChanges saved to: {changes_file}")
    
    changes = parse_block_changes(selected_response)
    preview_and_apply_changes(changes, workdir, config.test_cmd)

def replay_saved_file(filepath: Path, claude: ClaudeAPIAgent, workdir: Path, raw: bool = False) -> None:
    """Process a saved prompt file and display the response"""
    if not filepath.exists():
        raise FileNotFoundError(f"File {filepath} not found")
    
    content = filepath.read_text()
    
    # Add debug output of file content
    if config.debug:
        console = Console()
        console.print("\n[bold blue]Debug: File Content[/bold blue]")
        console.print(Panel(
            content,
            title=f"Content of {filepath.name}",
            border_style="blue",
            padding=(1, 2)
        ))
        console.print()

    file_type = get_history_file_type(filepath)
    
    if file_type == 'changes':
        success, _ = handle_changes_file(filepath, workdir, config.test_cmd)
        if not success:
            raise typer.Exit(1)
    elif file_type == 'analysis':
        format_analysis(content, raw, claude)
        handle_option_selection(claude, content, content, raw, workdir)
    elif file_type == 'selected':
        if raw:
            console = Console()
            console.print("\n=== Prompt Content ===")
            console.print(content)
            console.print("=== End Prompt Content ===\n")
        
        response = progress_send_message(claude, content)
        changes_file = save_to_file(response, 'changes_', workdir)
        print(f"\nChanges saved to: {changes_file}")
        
        changes = parse_block_changes(response)
        preview_and_apply_changes(changes, workdir, config.test_cmd)
    else:
        response = progress_send_message(claude, content)
        format_analysis(response, raw)

def process_question(question: str, workdir: Path, include: List[Path], raw: bool, claude: ClaudeAPIAgent) -> None:
    """Process a question about the codebase"""
    paths_to_scan = [workdir] if workdir else []
    if include:
        paths_to_scan.extend(include)
    files_content = collect_files_content(paths_to_scan, workdir)
    answer = ask_question(question, files_content, claude)
    display_answer(answer, raw)

def ensure_workdir(workdir: Path) -> Path:
    """Ensure working directory exists, prompt for creation if it doesn't"""
    if workdir.exists():
        return workdir
        
    console = Console()
    console.print(f"\n[yellow]Directory does not exist:[/yellow] {workdir}")
    if Confirm.ask("Create directory?"):
        workdir.mkdir(parents=True)
        console.print(f"[green]Created directory:[/green] {workdir}")
        return workdir
    raise typer.Exit(1)

def typer_main(
    request: Optional[str] = typer.Argument(None, help="The modification request"),
    ask: Optional[str] = typer.Option(None, "--ask", help="Ask a question about the codebase"),
    workdir: Optional[Path] = typer.Option(None, "-w", "--workdir", 
                                         help="Working directory (defaults to current directory)", 
                                         file_okay=False, dir_okay=True),
    raw: bool = typer.Option(False, "--raw", help="Print raw response instead of markdown format"),
    play: Optional[Path] = typer.Option(None, "--play", help="Replay a saved prompt file"),
    include: Optional[List[Path]] = typer.Option(None, "-i", "--include", help="Additional paths to include in analysis", exists=True),
    debug: bool = typer.Option(False, "--debug", help="Show debug information"),
    verbose: bool = typer.Option(False, "-v", "--verbose", help="Show verbose output"),
    scan: bool = typer.Option(False, "--scan", help="Preview files that would be analyzed"),
    version: bool = typer.Option(False, "--version", help="Show version and exit"),
    test: Optional[str] = typer.Option(None, "-t", "--test", help="Test command to run before applying changes"),
) -> None:
    """
    Analyze files and provide modification instructions.
    """
    if version:
        console = Console()
        console.print(f"Janito v{get_version()}")
        raise typer.Exit()

    config.set_debug(debug)
    config.set_verbose(verbose)
    config.set_test_cmd(test)

    claude = ClaudeAPIAgent(system_prompt=SYSTEM_PROMPT)

    if not any([request, ask, play, scan]):
        workdir = workdir or Path.cwd()
        workdir = ensure_workdir(workdir)
        from janito.console import start_console_session
        start_console_session(workdir, include)
        return

    workdir = workdir or Path.cwd()
    workdir = ensure_workdir(workdir)
    
    if include:
        include = [
            path if path.is_absolute() else (workdir / path).resolve()
            for path in include
        ]
    
    if ask:
        process_question(ask, workdir, include, raw, claude)
        return

    if scan:
        paths_to_scan = include if include else [workdir]
        preview_scan(paths_to_scan, workdir)
        return

    if play:
        replay_saved_file(play, claude, workdir, raw)
        return

    paths_to_scan = include if include else [workdir]
    
    is_empty = is_dir_empty(workdir)
    if is_empty and not include:
        console = Console()
        console.print("\n[bold blue]Empty directory - will create new files as needed[/bold blue]")
        files_content = ""
    else:
        files_content = collect_files_content(paths_to_scan, workdir)
    
    initial_prompt = build_request_analysis_prompt(files_content, request)
    initial_response = progress_send_message(claude, initial_prompt)
    save_to_file(initial_response, 'analysis', workdir)
    
    format_analysis(initial_response, raw, claude)
    
    handle_option_selection(claude, initial_response, request, raw, workdir, include)

def main():
    typer.run(typer_main)

if __name__ == "__main__":
    main()