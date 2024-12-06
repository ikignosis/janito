from pathlib import Path
from typing import Dict, Tuple, Optional, List
import tempfile
import shutil
import subprocess
from rich.console import Console
from rich.prompt import Confirm
from rich.panel import Panel
from rich import box
from janito.fileparser import FileChange, validate_python_syntax
from janito.changeviewer import preview_all_changes
from janito.contextparser import apply_changes, parse_change_block
from janito.config import config  # Add this import

def run_test_command(preview_dir: Path, test_cmd: str) -> Tuple[bool, str, Optional[str]]:
    """Run test command in preview directory.
    Returns (success, output, error)"""
    try:
        result = subprocess.run(
            test_cmd,
            shell=True,
            cwd=preview_dir,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        return (
            result.returncode == 0,
            result.stdout,
            result.stderr if result.returncode != 0 else None
        )
    except subprocess.TimeoutExpired:
        return False, "", "Test command timed out after 5 minutes"
    except Exception as e:
        return False, "", f"Error running test: {str(e)}"

def format_context_preview(lines: List[str], max_lines: int = 5) -> str:
    """Format context lines for display, limiting the number of lines shown"""
    if not lines:
        return "No context lines"
    preview = lines[:max_lines]
    suffix = f"\n... and {len(lines) - max_lines} more lines" if len(lines) > max_lines else ""
    return "\n".join(preview) + suffix

def format_whitespace_debug(text: str) -> str:
    """Format text with visible whitespace markers"""
    return text.replace(' ', '·').replace('\t', '→').replace('\n', '↵\n')

def parse_and_apply_changes_sequence(input_text: str, changes_text: str) -> str:
    """
    Parse and apply changes to text:
    = Find and keep line (preserving whitespace)
    < Remove line at current position
    > Add line at current position
    """
    def find_initial_start(text_lines, sequence):
        for i in range(len(text_lines) - len(sequence) + 1):
            matches = True
            for j, seq_line in enumerate(sequence):
                if text_lines[i + j] != seq_line:
                    matches = False
                    break
            if matches:
                return i
                
            if config.debug and i < 20:  # Show first 20 attempted matches
                console = Console()
                console.print(f"\n[cyan]Checking position {i}:[/cyan]")
                for j, seq_line in enumerate(sequence):
                    if i + j < len(text_lines):
                        match_status = "=" if text_lines[i + j] == seq_line else "≠"
                        console.print(f"  {match_status} Expected: '{seq_line}'")
                        console.print(f"    Found:    '{text_lines[i + j]}'")
        return -1

    input_lines = input_text.splitlines()
    changes = changes_text.splitlines()    
    
    sequence = []
    # Find the context sequence in the input text
    for line in changes:
        if line[0] == '=':
            sequence.append(line[1:])
        else:
            break
    
    start_pos = find_initial_start(input_lines, sequence)
    
    if start_pos == -1:
        if config.debug:
            console = Console()
            console.print("\n[red]Failed to find context sequence match in file:[/red]")
            console.print("[yellow]File content:[/yellow]")
            for i, line in enumerate(input_lines):
                console.print(f"  {i+1:2d} | '{line}'")
        return input_text
        
    if config.debug:
        console = Console()
        console.print(f"\n[green]Found context match at line {start_pos + 1}[/green]")
    
    result_lines = input_lines[:start_pos]
    i = start_pos
    
    for change in changes:
        if not change:
            if config.debug:
                console.print(f"  Preserving empty line")
            continue
            
        prefix = change[0]
        content = change[1:]
        
        if prefix == '=':
            if config.debug:
                console.print(f"  Keep: '{content}'")
            result_lines.append(content)
            i += 1
        elif prefix == '<':
            if config.debug:
                console.print(f"  Delete: '{content}'")
            i += 1
        elif prefix == '>':
            if config.debug:
                console.print(f"  Add: '{content}'")
            result_lines.append(content)
            
    result_lines.extend(input_lines[i:])
    
    if config.debug:
        console.print("\n[yellow]Final result:[/yellow]")
        for i, line in enumerate(result_lines):
            console.print(f"  {i+1:2d} | '{line}'")
            
    return '\n'.join(result_lines)

def normalize_content(text: str) -> str:
    """Normalize text for searching by removing line endings and normalizing whitespace"""
    # Convert all line endings to \n first
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    # Strip line endings for comparison while preserving internal whitespace
    return text.strip('\n')

def apply_single_change(filepath: Path, change: FileChange, workdir: Path, preview_dir: Path) -> Tuple[bool, Optional[str]]:
    """Apply a single file change"""
    preview_path = preview_dir / filepath
    preview_path.parent.mkdir(parents=True, exist_ok=True)
    
    if change.is_new_file:
        preview_path.write_text(change.content)
        return True, None
        
    # For modifications, read original and apply all search/replace blocks
    orig_path = workdir / filepath
    if not orig_path.exists():
        return False, f"Cannot modify non-existent file {filepath}"
        
    content = orig_path.read_text()
    modified = content
    
    for search, replace in change.search_blocks:
        # Normalize for searching but keep original for display
        normalized_search = normalize_content(search)
        normalized_content = normalize_content(modified)
        
        if normalized_search not in normalized_content:
            # Format both search text and file content to show whitespace
            debug_search = format_whitespace_debug(search)
            debug_content = format_whitespace_debug(modified)
            error_msg = (
                f"Could not find search text in {filepath}:\n\n"
                f"[yellow]Search text (with whitespace markers):[/yellow]\n"
                f"{debug_search}\n\n"
                f"[yellow]File content (with whitespace markers):[/yellow]\n"
                f"{debug_content}"
            )
            return False, error_msg
            
        # Use original text for replacement to preserve line endings
        modified = modified.replace(normalized_search, "" if replace is None else replace)
        
    if modified == content:
        return False, "No changes were applied"
        
    preview_path.write_text(modified)
    return True, None

def preview_and_apply_changes(changes: Dict[Path, FileChange], workdir: Path, test_cmd: str = None) -> bool:
    """Preview changes and apply if confirmed"""
    console = Console()
    
    if not changes:
        console.print("\n[yellow]No changes were found to apply[/yellow]")
        return False

    # Show change preview before applying
    preview_all_changes(console, changes)


    with tempfile.TemporaryDirectory() as temp_dir:
        preview_dir = Path(temp_dir)
        console.print("\n[blue]Creating preview in temporary directory...[/blue]")
        
        # Copy existing files
        if workdir.exists():
            shutil.copytree(workdir, preview_dir, dirs_exist_ok=True)
        
        # Apply changes to preview directory
        any_errors = False
        for filepath, change in changes.items():
            console.print(f"[dim]Previewing changes for {filepath}...[/dim]")
            success, error = apply_single_change(filepath, change, workdir, preview_dir)
            if not success:
                console.print(f"\n[red]Error previewing changes for {filepath}:[/red]")
                console.print(f"[red]{error}[/red]")
                any_errors = True
                continue
        
        if any_errors:
            console.print("\n[red]Some changes could not be previewed. Aborting.[/red]")
            return False

        # Validate Python syntax for all modified Python files
        python_files = [f for f in changes.keys() if f.suffix == '.py']
        for filepath in python_files:
            preview_path = preview_dir / filepath
            is_valid, error_msg = validate_python_syntax(preview_path.read_text(), preview_path)
            if not is_valid:
                console.print(f"\n[red]Python syntax validation failed for {filepath}:[/red]")
                console.print(f"[red]{error_msg}[/red]")
                return False

        # Run tests if specified
        if test_cmd:
            console.print(f"\n[cyan]Testing changes in preview directory:[/cyan] {test_cmd}")
            success, output, error = run_test_command(preview_dir, test_cmd)
            
            if output:
                console.print("\n[bold]Test Output:[/bold]")
                console.print(Panel(output, box=box.ROUNDED))
            
            if not success:
                console.print("\n[red bold]Tests failed in preview. Changes will not be applied.[/red bold]")
                if error:
                    console.print(Panel(error, title="Error", border_style="red"))
                return False

        # Final confirmation to apply to working directory
        if not Confirm.ask("\n[cyan bold]Apply previewed changes to working directory?[/cyan bold]"):
            console.print("\n[yellow]Changes were only previewed, not applied to working directory[/yellow]")
            return False

        # Copy changes to actual files
        console.print("\n[blue]Applying changes to working directory...[/blue]")
        for filepath, _ in changes.items():
            console.print(f"[dim]Applying changes to {filepath}...[/dim]")
            preview_path = preview_dir / filepath
            target_path = workdir / filepath
            target_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(preview_path, target_path)

        console.print("\n[green]Changes successfully applied to working directory![/green]")
        return True