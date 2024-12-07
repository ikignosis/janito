from pathlib import Path
from typing import Dict, Tuple, Optional, List
import tempfile
import shutil
import subprocess
from rich.console import Console
from rich.prompt import Confirm
from rich.panel import Panel
from rich import box
from datetime import datetime
from janito.fileparser import FileChange, validate_python_syntax
from janito.changeviewer import preview_all_changes
from janito.contextparser import apply_changes, parse_change_block
from janito.config import config

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

def get_line_boundaries(text: str) -> List[Tuple[int, int, int, int]]:
    """Return list of (content_start, content_end, full_start, full_end) for each line.
    content_start/end exclude leading/trailing whitespace
    full_start/end include the whitespace and line endings"""
    boundaries = []
    start = 0
    for line in text.splitlines(keepends=True):
        content = line.strip()
        if content:
            content_start = start + len(line) - len(line.lstrip())
            content_end = start + len(line.rstrip())
            boundaries.append((content_start, content_end, start, start + len(line)))
        else:
            # Empty or whitespace-only lines
            boundaries.append((start, start, start, start + len(line)))
        start += len(line)
    return boundaries

def normalize_content(text: str) -> Tuple[str, List[Tuple[int, int, int, int]]]:
    """Normalize text for searching while preserving position mapping.
    Returns (normalized_text, line_boundaries)"""
    # Replace Windows line endings
    text = text.replace('\r\n', '\n')
    text = text.replace('\r', '\n')
    
    # Get line boundaries before normalization
    boundaries = get_line_boundaries(text)
    
    # Create normalized version with stripped lines
    normalized = '\n'.join(line.strip() for line in text.splitlines())
    
    return normalized, boundaries

def find_text_positions(text: str, search: str) -> List[Tuple[int, int]]:
    """Find all non-overlapping positions of search text in content,
    comparing without leading/trailing whitespace but returning original positions."""
    normalized_text, text_boundaries = normalize_content(text)
    normalized_search, search_boundaries = normalize_content(search)
    
    positions = []
    start = 0
    while True:
        # Find next occurrence in normalized text
        pos = normalized_text.find(normalized_search, start)
        if pos == -1:
            break
            
        # Find the corresponding original text boundaries
        search_lines = normalized_search.count('\n') + 1
        
        # Get text line number at position
        line_num = normalized_text.count('\n', 0, pos)
        
        if line_num + search_lines <= len(text_boundaries):
            # Get original start position from first line
            orig_start = text_boundaries[line_num][2]  # full_start
            # Get original end position from last line
            orig_end = text_boundaries[line_num + search_lines - 1][3]  # full_end
            
            positions.append((orig_start, orig_end))
        
        start = pos + len(normalized_search)
    
    return positions

def adjust_indentation(original: str, replacement: str) -> str:
    """Adjust replacement text indentation based on original text"""
    if not original or not replacement:
        return replacement
        
    # Get first non-empty lines to compare indentation
    orig_lines = original.splitlines()
    repl_lines = replacement.splitlines()
    
    orig_first = next((l for l in orig_lines if l.strip()), '')
    repl_first = next((l for l in repl_lines if l.strip()), '')
    
    # Calculate indentation difference
    orig_indent = len(orig_first) - len(orig_first.lstrip())
    repl_indent = len(repl_first) - len(repl_first.lstrip())
    indent_delta = orig_indent - repl_indent
    
    if indent_delta == 0:
        return replacement
        
    # Adjust indentation for all lines
    adjusted_lines = []
    for line in repl_lines:
        if not line.strip():  # Preserve empty lines
            adjusted_lines.append(line)
            continue
        
        current_indent = len(line) - len(line.lstrip())
        new_indent = max(0, current_indent + indent_delta)
        adjusted_lines.append(' ' * new_indent + line.lstrip())
    
    return '\n'.join(adjusted_lines)

def apply_single_change(filepath: Path, change: FileChange, workdir: Path, preview_dir: Path) -> Tuple[bool, Optional[str]]:
    """Apply a single file change"""
    preview_path = preview_dir / filepath
    preview_path.parent.mkdir(parents=True, exist_ok=True)
    
    if config.debug:
        console = Console()
        console.print(f"\n[cyan]Processing change for {filepath}[/cyan]")
        console.print(f"[dim]Change type: {'new file' if change.is_new_file else 'modification'}[/dim]")
    
    if change.is_new_file:
        if config.debug:
            console.print("[cyan]Creating new file with content:[/cyan]")
            console.print(Panel(change.content, title="New File Content"))
        preview_path.write_text(change.content)
        return True, None
        
    orig_path = workdir / filepath
    if not orig_path.exists():
        return False, f"Cannot modify non-existent file {filepath}"
        
    content = orig_path.read_text()
    modified = content
    
    for search, replace, description in change.search_blocks:
        if config.debug:
            console.print(f"\n[cyan]Processing search block:[/cyan] {description or 'no description'}")
            console.print("[yellow]Search text:[/yellow]")
            console.print(Panel(format_whitespace_debug(search)))
            if replace is not None:
                console.print("[yellow]Replace with:[/yellow]")
                console.print(Panel(format_whitespace_debug(replace)))
            else:
                console.print("[yellow]Action:[/yellow] Delete text")
                
        positions = find_text_positions(modified, search)
        
        if config.debug:
            console.print(f"[cyan]Found {len(positions)} matches[/cyan]")
        
        if not positions:
            error_context = f" ({description})" if description else ""
            debug_search = format_whitespace_debug(search)
            debug_content = format_whitespace_debug(modified)
            error_msg = (
                f"Could not find search text in {filepath}{error_context}:\n\n"
                f"[yellow]Search text (with whitespace markers):[/yellow]\n"
                f"{debug_search}\n\n"
                f"[yellow]File content (with whitespace markers):[/yellow]\n"
                f"{debug_content}"
            )
            return False, error_msg
            
        # Apply replacements from end to start to maintain position validity
        for start, end in reversed(positions):
            if config.debug:
                console.print(f"\n[cyan]Replacing text at positions {start}-{end}:[/cyan]")
                console.print("[yellow]Original segment:[/yellow]")
                console.print(Panel(format_whitespace_debug(modified[start:end])))
                if replace is not None:
                    console.print("[yellow]Replacing with:[/yellow]")
                    console.print(Panel(format_whitespace_debug(replace)))
            
            # Adjust replacement text indentation
            original_segment = modified[start:end]
            adjusted_replace = adjust_indentation(original_segment, replace) if replace else ""
            
            if config.debug and replace:
                console.print("[yellow]Adjusted replacement:[/yellow]")
                console.print(Panel(format_whitespace_debug(adjusted_replace)))
                    
            modified = modified[:start] + adjusted_replace + modified[end:]
    
    if modified == content:
        if config.debug:
            console.print("\n[yellow]No changes were applied to the file[/yellow]")
        return False, "No changes were applied"
        
    if config.debug:
        console.print("\n[green]Changes applied successfully[/green]")
        
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
        
        # Create backup directory
        backup_dir = workdir / '.janito' / 'backups' / datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_dir.parent.mkdir(parents=True, exist_ok=True)
        
        # Copy existing files to preview directory
        if workdir.exists():
            # Create backup before applying changes
            if config.verbose:
                console.print(f"[blue]Creating backup at:[/blue] {backup_dir}")
            shutil.copytree(workdir, backup_dir, ignore=shutil.ignore_patterns('.janito'))
            # Copy to preview directory
            shutil.copytree(workdir, preview_dir, dirs_exist_ok=True)
            
            # Create restore script
            restore_script = workdir / '.janito' / 'restore.sh'
            restore_script.parent.mkdir(parents=True, exist_ok=True)
            script_content = f"""#!/bin/bash
# Restore script generated by Janito
# Restores files from backup created at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

# Exit on error
set -e

# Check if backup directory exists
if [ ! -d "{backup_dir}" ]; then
    echo "Error: Backup directory not found at {backup_dir}"
    exit 1
fi

# Restore files from backup
echo "Restoring files from backup..."
cp -r "{backup_dir}"/* "{workdir}/"

echo "Files restored successfully from {backup_dir}"
"""
            restore_script.write_text(script_content)
            restore_script.chmod(0o755)  # Make script executable
            
            if config.verbose:
                console.print(f"[blue]Created restore script at:[/blue] {restore_script}")
        
    
    # Apply changes to preview directory
        any_errors = False
        for filepath, change in changes.items():
            console.print(f"[dim]Previewing changes for {filepath}...[/dim]")
            success, error = apply_single_change(filepath, change, workdir, preview_dir)
            if not success:
                if "file already exists" in str(error):
                    console.print(f"\n[red]Error: Cannot create {filepath}[/red]")
                    console.print("[red]File already exists and overwriting is not allowed.[/red]")
                else:
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