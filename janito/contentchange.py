import re
from pathlib import Path
from typing import Dict, Tuple, TypedDict, List
from rich.console import Console
from rich.prompt import Confirm
import tempfile
from janito.changeviewer import show_file_changes, FileChange, show_diff_changes
import ast
from datetime import datetime
import shutil
import subprocess

def get_file_type(filepath: Path) -> str:
    """Determine the type of saved file based on its name"""
    name = filepath.name.lower()
    if 'changes' in name:
        return 'changes'
    elif 'selected' in name:
        return 'selected'
    elif 'analysis' in name:
        return 'analysis'
    elif 'response' in name:
        return 'response'
    return 'unknown'

def parse_block_changes(content: str) -> Dict[Path, FileChange]:
    """Parse file changes from code blocks in the content.
    Returns dict mapping filepath -> FileChange"""
    changes = {}
    
    # Extract the UUID from the first block
    uuid_pattern = r'##\s*([\da-f]{8})\s+([^\n]+)\s+begin\s*"([^"]*)"[^\n]*##'
    uuid_match = re.search(uuid_pattern, content)
    if not uuid_match:
        return changes  # No UUID found, return empty changes
    
    uuid = uuid_match.group(1)
    
    # Use the extracted UUID to find all blocks
    pattern = rf'##\s*{uuid}\s+([^\n]+)\s+begin\s*"([^"]*)"[^\n]*##\n(.*?)##\s*{uuid}\s+\1\s+end\s*##'
    matches = re.finditer(pattern, content, re.DOTALL)
    
    console = Console()
    
    for match in matches:
        filepath = Path(match.group(1))
        description = match.group(2)
        file_content = match.group(3).strip()
        
        # Check for incomplete file content marker
        if '[... rest of the file content remains unchanged ...]' in file_content:
            console.print(f"\n[red bold]⚠️ Error: File {filepath} contains incomplete content marker[/red bold]")
            console.print("[yellow]This indicates the file is too large and needs to be split into smaller chunks.[/yellow]")
            console.print("[yellow]Please modify your request to focus on specific parts of the file.[/yellow]")
            return {}
        
        changes[filepath] = FileChange(
            description=description,
            new_content=file_content
        )
        
    return changes

def save_changes_to_history(content: str, request: str, workdir: Path) -> Path:
    """Save change content to history folder with timestamp and request info"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")  # Already in the correct format
    history_dir = workdir / '.janito' / 'history'
    history_dir.mkdir(parents=True, exist_ok=True)
    
    # Create history entry with request and changes
    history_file = history_dir / f"changes_{timestamp}.txt"
    
    history_content = f"""Request: {request}
Timestamp: {timestamp}

Changes:
{content}
"""
    history_file.write_text(history_content)
    return history_file

def process_and_save_changes(content: str, request: str, workdir: Path) -> Tuple[Dict[Path, Tuple[str, str]], Path]:
    """Parse changes and save to history, returns (changes_dict, history_file)"""
    changes = parse_block_changes(content)
    history_file = save_changes_to_history(content, request, workdir)
    return changes, history_file

def validate_python_syntax(content: str, filepath: Path) -> Tuple[bool, str]:
    """Validate Python syntax and return (is_valid, error_message)"""
    try:
        ast.parse(content)
        return True, ""
    except SyntaxError as e:
        return False, f"Line {e.lineno}: {e.msg}"

def format_parsed_changes(changes: Dict[Path, Tuple[str, str]]) -> str:
    """Format parsed changes to show only file change descriptions"""
    result = []
    for filepath, (_, description) in changes.items():  # Updated tuple unpacking
        result.append(f"=== {filepath} ===\n{description}\n")
    return "\n".join(result)

def validate_changes(changes: Dict[Path, FileChange]) -> Tuple[bool, List[Tuple[Path, str]]]:
    """Validate all changes, returns (is_valid, list of errors)"""
    errors = []
    for filepath, change in changes.items():
        if filepath.suffix == '.py':
            is_valid, error = validate_python_syntax(change['new_content'], filepath)
            if not is_valid:
                errors.append((filepath, error))
    return len(errors) == 0, errors

def run_test_command(preview_dir: Path, test_cmd: str) -> Tuple[bool, str]:
    """Run test command in preview directory and return success status and output"""
    console = Console()
    console.print(f"\n[cyan]Running test command:[/cyan] {test_cmd}")
    
    try:
        result = subprocess.run(
            test_cmd,
            shell=True,
            cwd=preview_dir,
            capture_output=True,
            text=True
        )
        success = result.returncode == 0
        output = result.stdout + result.stderr
        return success, output
    except Exception as e:
        return False, str(e)

def preview_and_apply_changes(changes: Dict[Path, FileChange], workdir: Path, test_cmd: str = None) -> bool:
    """Preview changes in temporary directory and apply if confirmed."""
    console = Console()

    if not changes:
        console.print("\n[yellow]No changes were found to apply[/yellow]")
        return False

    with tempfile.TemporaryDirectory() as temp_dir:
        preview_dir = Path(temp_dir)
        if workdir.exists():
            shutil.copytree(workdir, preview_dir, dirs_exist_ok=True)
        
        for filepath, change in changes.items():
            # Get original content
            orig_path = workdir / filepath
            original = orig_path.read_text() if orig_path.exists() else ""
            
            # Prepare preview
            preview_path = preview_dir / filepath
            preview_path.parent.mkdir(parents=True, exist_ok=True)
            preview_path.write_text(change['new_content'])
            
            # Show changes
            show_diff_changes(console, filepath, original, change['new_content'], change['description'])

        # Run test command if provided
        if test_cmd:
            test_success, test_output = run_test_command(preview_dir, test_cmd)
            console.print("\n[bold]Test Results:[/bold]")
            console.print(test_output)
            
            if not test_success:
                console.print("\n[red]⚠️ Tests failed! Changes will not be applied.[/red]")
                return False

        # Apply changes if confirmed
        if Confirm.ask("\nApply these changes?"):
            for filepath, _ in changes.items():
                preview_path = preview_dir / filepath
                target_path = workdir / filepath
                target_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(preview_path, target_path)
                console.print(f"[green]✓[/green] Applied changes to {filepath}")
            return True
            
    return False

def apply_content_changes(content: str, request: str, workdir: Path, test_cmd: str = None) -> Tuple[bool, Path]:
    """Regular flow: Parse content, save to history, and apply changes."""
    console = Console()
    changes = parse_block_changes(content)
    
    if not changes:
        console.print("\n[yellow]No file changes were found in the response[/yellow]")
        return False, None

    # Validate changes before proceeding
    is_valid, errors = validate_changes(changes)
    if not is_valid:
        console = Console()
        console.print("\n[red bold]⚠️ Cannot apply changes: Python syntax errors detected![/red bold]")
        for filepath, error in errors:
            console.print(f"\n[red]⚠️ {filepath}: {error}[/red]")
        return False, None

    history_file = save_changes_to_history(content, request, workdir)
    success = preview_and_apply_changes(changes, workdir, test_cmd)
    return success, history_file

def handle_changes_file(filepath: Path, workdir: Path, test_cmd: str = None) -> Tuple[bool, Path]:
    """Replay flow: Load changes from file and apply them."""
    content = filepath.read_text()
    changes = parse_block_changes(content)
    
    if not changes:
        console = Console()
        console.print("\n[yellow]No file changes were found in the file[/yellow]")
        return False, None

    success = preview_and_apply_changes(changes, workdir, test_cmd)
    return success, filepath