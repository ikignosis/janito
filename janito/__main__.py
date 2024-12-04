import typer
from typing import Optional, Dict, Any, List
from pathlib import Path
from janito.claude import ClaudeAPIAgent
import shutil  # Add shutil import
from janito.prompts import (
    build_request_analisys_prompt,
    build_selected_option_prompt,
    SYSTEM_PROMPT
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
    format_parsed_changes  # Add this import
)
from rich.table import Table
from rich.columns import Columns
from rich.panel import Panel
from rich.text import Text
from rich.rule import Rule
from rich import box
from datetime import datetime, UTC  # Add UTC import
from itertools import chain
from janito.scan import collect_files_content, is_dir_empty, preview_scan  # Add preview_scan import
from janito.qa import ask_question, display_answer
from rich.prompt import Prompt
from janito.config import config

def format_analysis(analysis: str, raw: bool = False, claude: Optional[ClaudeAPIAgent] = None) -> None:
    """Format and display the analysis output"""
    console = Console()
    if raw and claude:
        console.print("\n=== Message History ===")
        for role, content in claude.messages_history:
            console.print(f"\n[bold cyan]{role.upper()}:[/bold cyan]")
            console.print(content)
        console.print("\n=== End Message History ===\n")
    else:
        md = Markdown(analysis)
        console.print(md)

def prompt_user(message: str, choices: List[str] = None) -> str:
    """Display a prominent user prompt with optional choices"""
    console = Console()
    console.print()
    console.print(Rule(" User Input Required ", style="bold cyan"))
    
    if choices:
        choice_text = f"[cyan]Options: {', '.join(choices)}[/cyan]"
        console.print(Panel(choice_text, box=box.ROUNDED))
    
    return Prompt.ask(f"[bold cyan]> {message}[/bold cyan]")

def get_option_selection() -> int:
    """Get user input for option selection"""
    while True:
        try:
            option = int(prompt_user("Select option number"))
            return option
        except ValueError:
            console = Console()
            console.print("[red]Please enter a valid number[/red]")

def get_history_path(workdir: Path) -> Path:
    """Create and return the history directory path"""
    history_dir = workdir / '.janito' / 'history'
    history_dir.mkdir(parents=True, exist_ok=True)
    return history_dir

def get_timestamp() -> str:
    """Get current UTC timestamp in YMD_HMS format with leading zeros"""
    return datetime.now(UTC).strftime('%Y%m%d_%H%M%S')

def save_prompt_to_file(prompt: str) -> Path:
    """Save prompt to a named temporary file that won't be deleted"""
    temp_file = tempfile.NamedTemporaryFile(prefix='selected_', suffix='.txt', delete=False)
    temp_path = Path(temp_file.name)
    temp_path.write_text(prompt)
    return temp_path

def save_to_file(content: str, prefix: str, workdir: Path) -> Path:
    """Save content to a timestamped file in history directory"""
    history_dir = get_history_path(workdir)
    timestamp = get_timestamp()
    filename = f"{timestamp}_{prefix}.txt"
    file_path = history_dir / filename
    file_path.write_text(content)
    return file_path

def handle_option_selection(claude: ClaudeAPIAgent, initial_response: str, request: str, raw: bool = False, workdir: Optional[Path] = None, include: Optional[List[Path]] = None) -> None:
    """Handle option selection and implementation details"""
    option = get_option_selection()
    # Get current files content with included paths
    paths_to_scan = [workdir] if workdir else []
    if include:
        paths_to_scan.extend(include)
    files_content = collect_files_content(paths_to_scan, workdir) if paths_to_scan else ""
    
    selected_prompt = build_selected_option_prompt(option, request, initial_response, files_content)
    prompt_file = save_to_file(selected_prompt, 'selected', workdir)
    if config.verbose:
        print(f"\nSelected prompt saved to: {prompt_file}")
    
    selected_response = claude.send_message(selected_prompt)
    # Save response to changes file
    changes_file = save_to_file(selected_response, 'changes', workdir)
    if config.verbose:
        print(f"\nChanges saved to: {changes_file}")

    
    changes = parse_block_changes(selected_response)
    preview_and_apply_changes(changes, workdir)

def replay_saved_file(filepath: Path, claude: ClaudeAPIAgent, workdir: Path, raw: bool = False) -> None:
    """Process a saved prompt file and display the response"""
    if not filepath.exists():
        raise FileNotFoundError(f"File {filepath} not found")
    
    file_type = get_file_type(filepath)
    content = filepath.read_text()
    
    if file_type == 'changes':
        changes = parse_block_changes(content)  # Parse the changes file content
        preview_and_apply_changes(changes, workdir)  # Show preview and apply changes
    elif file_type == 'analysis':
        format_analysis(content, raw, claude)
        handle_option_selection(claude, content, content, raw, workdir)
    elif file_type == 'selected':
        if raw:
            console = Console()
            console.print("\n=== Prompt Content ===")
            console.print(content)
            console.print("=== End Prompt Content ===\n")
        response = claude.send_message(content)
        changes_file = save_to_file(response, 'changes_', workdir)
        print(f"\nChanges saved to: {changes_file}")
        
        changes = parse_block_changes(response)
        preview_and_apply_changes(changes, workdir)
    else:
        response = claude.send_message(content)
        format_analysis(response, raw)

def process_question(question: str, workdir: Path, include: List[Path], raw: bool, claude: ClaudeAPIAgent) -> None:
    """Process a question about the codebase"""
    paths_to_scan = [workdir] if workdir else []
    if include:
        paths_to_scan.extend(include)
    files_content = collect_files_content(paths_to_scan, workdir)

    answer = ask_question(question, files_content, claude)
    display_answer(answer, raw)

def parse_options(response: str) -> dict[int, str]:
    """Parse options from the response text"""
    options = {}
    pattern = r"===\s*\*\*Option (\d+)\*\*\s*:\s*(.+?)(?====\s*\*\*Option|\Z)"
    matches = re.finditer(pattern, response, re.DOTALL)

    for match in matches:
        option_num = int(match.group(1))
        option_text = match.group(2).strip()
        options[option_num] = option_text

    return options

def main(
    request: Optional[str] = typer.Argument(None, help="The modification request"),
    ask: Optional[str] = typer.Option(None, "--ask", help="Ask a question about the codebase"),
    workdir: Optional[Path] = typer.Option(None, "-w", "--workdir", help="Working directory (defaults to current directory)", exists=True, file_okay=False, dir_okay=True),
    raw: bool = typer.Option(False, "--raw", help="Print raw response instead of markdown format"),
    play: Optional[Path] = typer.Option(None, "--play", help="Replay a saved prompt file"),
    include: Optional[List[Path]] = typer.Option(None, "-i", "--include", help="Additional paths to include in analysis", exists=True),
    debug: bool = typer.Option(False, "--debug", help="Show debug information"),
    debug_line: Optional[int] = typer.Option(None, "--debug-line", help="Show debug information only for specific line number"),
    verbose: bool = typer.Option(False, "-v", "--verbose", help="Show verbose output"),
    scan: bool = typer.Option(False, "--scan", help="Preview files that would be analyzed"),
) -> None:

    """
    Analyze files and provide modification instructions.
    """
    config.set_debug(debug)
    config.set_verbose(verbose)
    config.set_debug_line(debug_line)  # Move this line after setting debug to ensure proper configuration order

    claude = ClaudeAPIAgent(system_prompt=SYSTEM_PROMPT)

    # Start console mode if no arguments provided
    if not any([request, ask, play, scan]):
        workdir = workdir or Path.cwd()
        from janito.console import start_console_session
        start_console_session(workdir, include)
        return



    # Use current directory if workdir not specified
    workdir = workdir or Path.cwd()
    
    # Convert included paths to absolute if they're relative
    if include:
        include = [
            path if path.is_absolute() else (workdir / path).resolve()
            for path in include
        ]
    
    if ask:
        process_question(ask, workdir, include, raw, claude)
        return

    if scan:  # Add scan handling
        # Only scan included paths if provided, otherwise scan workdir
        paths_to_scan = include if include else [workdir]
        preview_scan(paths_to_scan, workdir)
        return

    if play:
        replay_saved_file(play, claude, workdir, raw)
        return

    # Regular flow - same logic for scanning
    paths_to_scan = include if include else [workdir]
    
    is_empty = is_dir_empty(workdir)
    if is_empty and not include:
        console = Console()
        console.print("\n[bold blue]Empty directory - will create new files[/bold blue]")
        files_content = ""
    else:
        files_content = collect_files_content(paths_to_scan, workdir)
    
    # Get initial analysis and save it
    initial_prompt = build_request_analisys_prompt(files_content, request)
    initial_response = claude.send_message(initial_prompt)
    analysis_file = save_to_file(initial_response, 'analysis', workdir)
    print(f"\nAnalysis saved to: {analysis_file}")
    
    # Show initial response
    format_analysis(initial_response, raw, claude)
    
    # Always prompt for option selection
    handle_option_selection(claude, initial_response, request, raw, workdir, include)  # Remove debug parameter

if __name__ == "__main__":
    typer.run(main)
