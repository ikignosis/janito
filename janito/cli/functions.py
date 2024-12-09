from typing import Optional, List
from pathlib import Path
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
from rich.text import Text
from rich.markdown import Markdown
from datetime import datetime, timezone
import tempfile
import typer
import sys

from janito.agents import AIAgent
from janito.config import config
from janito.scan import collect_files_content, show_content_stats
from janito.analysis import (
    format_analysis, build_request_analysis_prompt, 
    parse_analysis_options, get_history_file_type, AnalysisOption
)
from janito.qa import ask_question, display_answer
from janito.common import progress_send_message
from janito.prompts import build_selected_option_prompt
from janito.fileparser import parse_block_changes
from janito.change.applier import preview_and_apply_changes

def prompt_user(message: str, choices: List[str] = None) -> str:
    """Display a simple user prompt with optional choices"""
    console = Console()
    
    if choices:
        console.print(f"\n[cyan]Options: {', '.join(choices)}[/cyan]")
    
    return Prompt.ask(f"[bold cyan]> {message}[/bold cyan]")

def validate_option_letter(letter: str, options: dict) -> bool:
    """Validate if the given letter is a valid option or 'M' for modify"""
    return letter.upper() in options or letter.upper() == 'M'

def get_option_selection() -> str:
    """Get user input for option selection"""
    console = Console()
    console.print("\n[cyan]Enter option letter or 'M' to modify request[/cyan]")
    
    while True:
        letter = Prompt.ask("[bold cyan]Select option[/bold cyan]").strip().upper()
        if letter == 'M' or (letter.isalpha() and len(letter) == 1):
            return letter
        
        console.print("[red]Please enter a valid letter or 'M'[/red]")

def get_change_history_path(workdir: Path) -> Path:
    """Create and return the changes history directory path"""
    changes_history_dir = workdir / '.janito' / 'change_history'
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
    changes_history_dir = get_change_history_path(workdir)
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

def format_option_text(option: AnalysisOption) -> str:
    """Format an AnalysisOption into a string representation"""
    option_text = f"Option {option.letter}:\n"
    option_text += f"Summary: {option.summary}\n\n"
    option_text += "Description:\n"
    for item in option.description_items:
        option_text += f"- {item}\n"
    option_text += "\nAffected files:\n"
    for file in option.affected_files:
        option_text += f"- {file}\n"
    return option_text

def handle_option_selection(initial_response: str, request: str, raw: bool = False, workdir: Optional[Path] = None, include: Optional[List[Path]] = None) -> None:
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
            # Only scan files listed in the selected option's affected_files
            selected_option = options[option]
            files_to_scan = selected_option.affected_files
    
            # Convert relative paths to absolute paths
            absolute_paths = []
            for file_path in files_to_scan:
                # Remove (new) suffix if present
                clean_path = file_path.split(' (')[0].strip()
                path = workdir / clean_path if workdir else Path(clean_path)
                if path.exists():
                    absolute_paths.append(path)
    
            files_content = collect_files_content(absolute_paths, workdir) if absolute_paths else ""   
            show_content_stats(files_content)         
            initial_prompt = build_request_analysis_prompt(files_content, new_request)
            initial_response = progress_send_message(initial_prompt)
            save_to_file(initial_response, 'analysis', workdir)
            
            format_analysis(initial_response, raw)
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

    # Only scan files listed in the selected option's affected_files
    selected_option = options[option]
    files_to_scan = selected_option.affected_files
    
    # Convert relative paths to absolute paths
    absolute_paths = []
    for file_path in files_to_scan:
        # Remove (new) suffix if present
        clean_path = file_path.split(' (')[0].strip()
        path = workdir / clean_path if workdir else Path(clean_path)
        if path.exists():
            absolute_paths.append(path)
    
    files_content = collect_files_content(absolute_paths, workdir) if absolute_paths else ""
    show_content_stats(files_content)
    
    # Format the selected option before building prompt
    selected_option = options[option]
    option_text = format_option_text(selected_option)
    
    selected_prompt = build_selected_option_prompt(option_text, request, files_content)
    prompt_file = save_to_file(selected_prompt, 'selected', workdir)
    if config.verbose:
        print(f"\nSelected prompt saved to: {prompt_file}")
    
    selected_response = progress_send_message(selected_prompt)
    changes_file = save_to_file(selected_response, 'changes', workdir)

    if config.verbose:
        try:
            rel_path = changes_file.relative_to(workdir)
            print(f"\nChanges saved to: ./{rel_path}")
        except ValueError:
            print(f"\nChanges saved to: {changes_file}")
    
    changes = parse_block_changes(selected_response)
    preview_and_apply_changes(changes, workdir, config.test_cmd)

def read_stdin() -> str:
    """Read input from stdin until EOF"""
    console = Console()
    console.print("[dim]Enter your input (press Ctrl+D when finished):[/dim]")
    return sys.stdin.read().strip()

def replay_saved_file(filepath: Path, workdir: Path, raw: bool = False) -> None:
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
        changes = parse_block_changes(content)
        success = preview_and_apply_changes(changes, workdir, config.test_cmd)
        if not success:
            raise typer.Exit(1)
    elif file_type == 'analysis':
        format_analysis(content, raw)
        handle_option_selection(content, content, raw, workdir)
    elif file_type == 'selected':
        if raw:
            console = Console()
            console.print("\n=== Prompt Content ===")
            console.print(content)
            console.print("=== End Prompt Content ===\n")
        
        response = progress_send_message(content)
        changes_file = save_to_file(response, 'changes_', workdir)
        print(f"\nChanges saved to: {changes_file}")
        
        changes = parse_block_changes(response)
        preview_and_apply_changes(changes, workdir, config.test_cmd)
    else:
        response = progress_send_message(content)
        format_analysis(response, raw)

def process_question(question: str, workdir: Path, include: List[Path], raw: bool, agent: AIAgent) -> None:
    """Process a question about the codebase"""
    paths_to_scan = [workdir] if workdir else []
    if include:
        paths_to_scan.extend(include)
    files_content = collect_files_content(paths_to_scan, workdir)
    answer = ask_question(question, files_content)
    display_answer(answer, raw)

def ensure_workdir(workdir: Path) -> Path:
    """Ensure working directory exists, prompt for creation if it doesn't"""
    if workdir.exists():
        return workdir.absolute()
        
    console = Console()
    console.print(f"\n[yellow]Directory does not exist:[/yellow] {workdir}")
    if Confirm.ask("Create directory?"):
        workdir.mkdir(parents=True)
        console.print(f"[green]Created directory:[/green] {workdir}")
        return workdir.absolute()
    raise typer.Exit(1)

def review_text(text: str, raw: bool = False) -> None:
    """Review the provided text using Claude"""
    console = Console()
    response = progress_send_message(f"Please review this text and provide feedback:\n\n{text}")
    if raw:
        console.print(response)
    else:
        console.print(Markdown(response))