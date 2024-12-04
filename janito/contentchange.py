import re
from pathlib import Path
from typing import Dict, Any, List
import tempfile
import shutil
import ast
from rich.console import Console
from rich.syntax import Syntax
from rich.panel import Panel
from rich.text import Text  # For assembling styled and escaped text
from rich.columns import Columns
from rich.rule import Rule
from rich import box
import json
from janito.changeviewer import format_parsed_changes  # Add this import
from janito.config import config
from datetime import datetime  # Add this import at the top with other imports

def verify_content_exists(filepath: Path, content: str) -> tuple[bool, str]:
    """Verify that specific content exists in a file, return (exists, details)"""
    if not filepath.exists():
        return False, f"File {filepath} does not exist"
        
    with open(filepath, 'r') as f:
        file_content = f.read()
    exists = content in file_content
    
    if not exists:
        # Find closest matching line for context
        lines = file_content.splitlines()
        content_lines = content.splitlines()
        details = []
        
        if content_lines:
            first_line = content_lines[0]
            if config.debug:
                console = Console()
                console.print("\n[cyan]Searching for first line:[/cyan]")
                console.print(Text(visualize_whitespace(first_line), no_wrap=True))
                console.print("\n[cyan]Available lines:[/cyan]")
            
            for i, line in enumerate(lines):
                if config.debug:
                    console.print(f"Line {i+1}: {Text(visualize_whitespace(line), no_wrap=True)}")
                if first_line in line:
                    details.append(f"Found similar content at line {i+1}:")
                    details.append(f"Expected:\n{visualize_whitespace(first_line)}")
                    details.append(f"Found   :\n{visualize_whitespace(line)}")
                    break
            else:
                if config.debug:
                    console.print("\n[red]No matching line found[/red]")
                details.append("No similar content found")
                details.append(f"Expected content first line: {first_line}")
        
        return False, "\n".join(details)
        
    if config.debug:
        console = Console()
        console.print(f"\n[cyan]Verifying content in {filepath}:[/cyan]")
        color = "green" if exists else "red"
        console.print(f"Content exists: [{color}]{exists}[/{color}]")
        
    return True, ""

def visualize_whitespace(text: str) -> str:
    """Convert whitespace characters to visible symbols"""
    return text.replace(' ', '·').replace('\n', '↵\n').replace('\t', '→')

def find_content_position(lines: List[str], original: str) -> tuple[int, int]:
    """Find the position of original content in lines and return start, end positions"""
    console = Console()
    original_lines = original.splitlines(keepends=True)
    original_len = len(original_lines)
    
    if config.debug and config.debug_line is None:
        console.print("\n[cyan]Looking for content ([bold cyan]original[/bold cyan]):[/cyan]")
        console.print(Text(visualize_whitespace(original), no_wrap=True))
        console.print("\n[cyan]In lines:[/cyan]")
    
    for i, line in enumerate(lines):
        chunk = ''.join(lines[i:i+original_len])
        if config.should_debug_line(i + 1):
            console.print(f"\n[cyan]Trying at position {i+1} debug_line={config.debug_line}:[/cyan]")
            console.print(Text(visualize_whitespace(chunk), no_wrap=True))
            if original.rstrip() != chunk.rstrip():
                console.print("[red]No match:[/red]")
                console.print(Text.assemble(
                    "Expected:\n",
                    Text(visualize_whitespace(original), style="yellow")
                ))
                console.print(Text.assemble(
                    "Found:\n",
                    Text(visualize_whitespace(chunk), style="yellow")
                ))
        # Compare with both line endings and leading whitespace stripped
        if original.rstrip().lstrip() == chunk.rstrip().lstrip():
            return i, i + original_len

            
    if config.debug:
        # Only show full debug output if no specific line was requested
        if config.debug_line is None:
            console.print("\n[red]Failed to find content match.[/red]")
            console.print("\n[yellow]Original content (with whitespace):[/yellow]")
            console.print(Text(visualize_whitespace(original), no_wrap=True))
            console.print("\n[yellow]Available lines (with whitespace):[/yellow]")
            for i, line in enumerate(lines, 1):
                console.print(Text(f"Line {i}: {visualize_whitespace(line)}", no_wrap=True), end="")  # Add end="" to prevent extra newline
                if i < len(lines):  # Only add newline if not the last line
                    console.print()
        else:
            console.print("\n[red]Content not found at any position[/red]")
            
    raise ValueError(f"Original content not found: {original}")

def validate_content_match(original: str, new: str) -> bool:
    """Validate that new content ends with original content, ignoring whitespace"""
    original = original.rstrip()
    new = new.rstrip()
    return new.endswith(original) or new.startswith(original)

def apply_file_changes(workdir: Path, change: Dict[str, Any]) -> None:
    """Apply a single file change from a block format
    
    Supported operations:
    - add_before_content: Inserts new text before a matched content block
        1. Find the position of the original content in the file
        2. Insert the new text with a newline at that position
        3. Original content remains unchanged and follows the inserted text
        Example:
            Original:
                def some_function():
                    pass
            Change:
                add_before_content:
                    original: "def some_function"
                    text: "# This is a new comment"
            Result:
                # This is a new comment
                def some_function():
                    pass
    """
    console = Console()
    filepath = workdir / change["filename"]

    if config.verbose:
        console.print(f"\n[cyan]→ Processing[/cyan] {filepath.name}")
    filepath.parent.mkdir(parents=True, exist_ok=True)
    
    # Handle new file creation
    if "content" in change:
        if filepath.exists():
            raise FileExistsError(f"Cannot create file {filepath}: File already exists")
        filepath.write_text(change["content"])
        console.print(f"  [green]✓ Created file[/green]")
        # Verify immediately after creation
        verify_changes(filepath, [change])
        return

    # Handle modifications to existing files
    if filepath.exists():
        content = filepath.read_text()

        if config.debug:
            console.print(f"\n[cyan]Original file content ({len(content)} chars):[/cyan]")
            console.print(Syntax(content, "python"))
    else:
        content = ""
        
    for c in change.get("changes", []):
        lines = content.splitlines(keepends=True)
        if config.debug:
            console.print(f"\n[cyan]Operation: {c['type']}[/cyan]")
            console.print(f"Original content to match ({len(c['original'])} chars):")
            text = Text(c["original"], no_wrap=True)
            console.print(text)
            console.print("Current lines:")
            for i, line in enumerate(lines):
                console.print(f"{i+1}: {repr(line)}")

        if c["type"] == "add_before_content":
            if not validate_content_match(c["original"], c["text"]):
                raise ValueError(f"New content must end with original content for add_before_content operation")
            start_pos, _ = find_content_position(lines, c["original"])
            new_content = c["text"][:-(len(c["original"]))]  # Remove original content from new text
            lines.insert(start_pos, new_content)
            content = ''.join(lines)
            filepath.write_text(content)

        elif c["type"] == "add_after_content":
            _, end_pos = find_content_position(lines, c["original"])
            # Check if the new content starts with the original content
            new_text = c["text"]
            if new_text.startswith(c["original"]):
                # Remove the duplicate content from the beginning
                new_text = new_text[len(c["original"]):].lstrip()
            lines.insert(end_pos, new_text + '\n')
            content = ''.join(lines)
            filepath.write_text(content)

        elif c["type"] == "replace_content":
            start_pos, end_pos = find_content_position(lines, c["original"])
            lines[start_pos:end_pos] = [c["text"] + '\n']
            content = ''.join(lines)
            filepath.write_text(content)

        elif c["type"] == "delete_content":
            start_pos, end_pos = find_content_position(lines, c["original"])
            del lines[start_pos:end_pos]
            content = ''.join(lines)
            filepath.write_text(content)
            
        if config.debug:
            console.print("\n[cyan]Content after operation:[/cyan]")
            console.print(Syntax(content, "python"))
    
    filepath.write_text(content)

def verify_changes(filepath: Path, changes: List[Dict[str, Any]]) -> None:
    """Verify function disabled - no checks performed"""
    # Verification disabled
    pass

def parse_block_changes(content: str) -> List[Dict[str, Any]]:
    """Parse block-format changes using a line-based approach"""
    console = Console()
    changes = []
    lines = content.splitlines()
    current_block = None
    current_section = None
    section_content = []
    
    # Error check and debug setup remain unchanged
    # ...existing code...
    
    for i, line in enumerate(lines):
        if config.debug:
            text = Text.assemble(
                (f"Line {i+1}:", "dim"),
                " ",
                Text(line, no_wrap=True),
            )
            console.print(text)

        # Check for block start - now only supports create_file and find_replace
        block_start = re.match(r'##\s*([\w-]+)\s+(.*?):(.*?)\s*##', line)
        if block_start:
            if current_block:
                raise ValueError("Found new block before previous block ended")
            uuid, filename, operation = (block_start.group(1), 
                                      block_start.group(2).strip(), 
                                      block_start.group(3).strip())
            if operation not in ['create_file', 'find_replace']:
                raise ValueError(f"Unsupported operation: {operation}")
            current_block = {
                'uuid': uuid,
                'filename': filename,
                'operation': operation,
                'original': None,
                'new': None
            }
            if config.debug:
                console.print(f"[yellow]Started block:[/yellow] {current_block}")
            continue
            
        # Check for block end
        if line.strip() == f"## {current_block['uuid']} end ##" if current_block else False:
            if current_section:
                current_block[current_section] = '\n'.join(section_content)
            
            # Process completed block - for create_file use content section, not new
            if current_block['operation'] == 'create_file':
                content_section = current_block.get('content', current_block.get('new'))  # Backwards compatibility
                if not content_section:
                    raise ValueError("Missing content for file creation")
                changes.append({
                    "filename": current_block['filename'],
                    "content": content_section.rstrip()  # Ensure content is properly stripped
                })
            else: # find_replace
                if not current_block.get('original') or not current_block.get('new'):
                    raise ValueError("Missing find or replace content for find_replace operation")
                changes.append({
                    "filename": current_block['filename'],
                    "changes": [{
                        "type": "replace_content",
                        "original": current_block['original'],
                        "text": current_block['new']
                    }]
                })
            
            current_block = None
            current_section = None
            section_content = []
            continue
            
        # Check for content sections - update to handle 'content' section
        if current_block:
            section_match = re.match(fr'##\s*{current_block["uuid"]}\s+(find|replace|new|content)\s*##', line)
            if section_match:
                if current_section:
                    current_block[current_section] = '\n'.join(section_content)
                section_type = section_match.group(1)
                current_section = {
                    'find': 'original',
                    'replace': 'new',
                    'new': 'new',
                    'content': 'content'
                }[section_type]
                section_content = []
                continue

    if current_block:
        raise ValueError("Block not properly closed")
    
    if config.debug:
        console.print("\n[bold red]DEBUG: Completed parsing[/bold red]")
        console.print("\n[cyan]Parsed changes:[/cyan]")
        console.print(json.dumps(changes, indent=2))
    
    return changes

def validate_python_syntax(filepath: Path) -> tuple[bool, str]:
    """Validate Python file syntax using ast"""
    try:
        with open(filepath, 'r') as f:
            source = f.read()
            ast.parse(source, filename=str(filepath))
        return True, ""
    except SyntaxError as e:
        # Extract error line and get surrounding context
        lines = source.splitlines()
        line_no = e.lineno
        start = max(0, line_no - 3)  # Show 3 lines before
        end = min(len(lines), line_no + 2)  # Show 2 lines after
        
        # Build error message with code context
        error_msg = [f"Syntax error in {filepath}: {str(e)}"]
        error_msg.append("\nRelevant code block:")
        
        for i in range(start, end):
            line = lines[i]
            line_prefix = f"{i+1:4d} "
            if i + 1 == line_no:
                error_msg.append(f"{line_prefix}>>> {line}  # Error occurs here")
            else:
                error_msg.append(f"{line_prefix}    {line}")
        
        return False, "\n".join(error_msg)

def create_preview_dir(workdir: Path) -> Path:
    """Create a preview directory and copy workspace contents"""
    preview_dir = tempfile.mkdtemp(prefix='preview_')
    preview_path = Path(preview_dir)
    
    # Copy workdir contents to preview directory, excluding .git
    if workdir.exists():
        for item in workdir.iterdir():
            if item.name != '.git':
                if item.is_dir():
                    shutil.copytree(item, preview_path / item.name)
                else:
                    shutil.copy2(item, preview_path / item.name)
    
    return preview_path

def preview_and_apply_changes(changes: List[Dict[str, Any]], workdir: Path) -> None:
    """Preview and handle applying changes to the workspace"""
    console = Console()
    
    # Show parsed changes using the new module
    format_parsed_changes(changes)
    
    # Create preview directory and show changes
    preview_path = create_preview_dir(workdir)
    console.print(f"\n[blue]Preview directory created at:[/blue] {preview_path}")
    
    # Track modified/created files
    changed_files = set()
    
    # Apply changes and verify each file immediately
    console.print("\n[bold cyan]Applying and verifying changes:[/bold cyan]")
    console.print("─" * 50)
    
    try:
        for change in changes:
            changed_file = preview_path / change["filename"]
            changed_files.add(changed_file)
            
            # Apply changes first
            apply_file_changes(preview_path, change)
            verify_changes(changed_file, [change])
            
            # Validate Python syntax if applicable
            if changed_file.suffix == '.py':
                is_valid, error = validate_python_syntax(changed_file)
                rel_path = changed_file.relative_to(preview_path)
                if is_valid:
                    console.print(f"[green]✓ Syntax valid:[/green] {rel_path}")
                else:
                    console.print(f"[red]✗ Syntax error:[/red] {rel_path}")
                    console.print(f"  [red]{error}[/red]")
                    return
                    
    except ValueError as e:
        console.print(f"\n[red]Error applying changes:[/red]")
        console.print(f"[red]{str(e)}[/red]")
        if config.debug:
            console.print("\n[yellow]Debug information available above[/yellow]")
        return

    console.print("\n[green]✓ All changes validated successfully[/green]")
    console.print(f"\n[blue]You can inspect the changes in the preview directory:[/blue] {preview_path}")
    
    # Ask for confirmation
    while True:
        response = input("\nApply changes to workspace? [y/n]: ").lower().strip()
        if response in ('y', 'n'):
            break
        console.print("[yellow]Please answer 'y' or 'n'[/yellow]")
    
    if response == 'n':
        console.print("[yellow]Changes aborted[/yellow]")
        console.print(f"[blue]Preview directory kept at:[/blue] {preview_path}")
        # Save changes to file and show path
        timestamp = datetime.now(UTC).strftime('%Y%m%d_%H%M%S')
        save_path = workdir / '.janito' / 'history' / f"{timestamp}_changes.txt"
        save_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert changes back to block format
        blocks = []
        for change in changes:
            if "content" in change:
                blocks.append(f"## create-file {change['filename']}: create_file ##\n")
                blocks.append(f"## create-file new ##\n")
                blocks.append(f"{change['content']}\n")
                blocks.append("## create-file end ##\n")
            else:
                for c in change.get("changes", []):
                    uuid = "change-" + datetime.now(UTC).strftime('%H%M%S')
                    blocks.append(f"## {uuid} {change['filename']}: {c['type']} ##\n")
                    blocks.append(f"## {uuid} original ##\n")
                    blocks.append(f"{c['original']}\n")
                    blocks.append(f"## {uuid} new ##\n")
                    blocks.append(f"{c['text']}\n")
                    blocks.append(f"## {uuid} end ##\n")
        
        save_path.write_text("".join(blocks))
        console.print(f"[blue]Changes saved to:[/blue] {save_path}")
        return

    # Apply verified changes
    console.print("\n[bold]Applying changes to workspace:[/bold]")
    for file_path in changed_files:
        rel_path = file_path.relative_to(preview_path)
        target_path = workdir / rel_path
        
        # Find the operation type for this file
        for change in changes:
            if change["filename"] == str(rel_path):
                if "content" in change:
                    operation = "Created new file"
                    style = "green"
                else:
                    ops = [c["type"] for c in change["changes"]]
                    operation = f"Modified ({', '.join(ops)})"
                    style = "yellow"
                break
        
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(file_path, target_path)
        console.print(f"[{style}]{operation}:[/{style}] {rel_path}")

    console.print(f"\n[green]Changes applied successfully to workspace:[/green] {workdir}")
    console.print(f"[blue]Preview directory kept at:[/blue] {preview_path}")

def handle_changes_file(filepath: Path, workdir: Path) -> None:
    """Legacy method - now just parses file and calls preview_and_apply_changes"""
    with open(filepath, 'r') as f:
        content = f.read()
    changes = parse_block_changes(content)
    preview_and_apply_changes(changes, workdir)

def get_file_type(filepath: Path) -> str:
    """Determine the type of saved file based on its prefix"""
    name = filepath.name
    if '_' not in name:
        raise ValueError(f"Invalid filename format: {name}. Expected format: timestamp_type.txt")
        
    # Split on underscore and get the last part before .txt
    parts = name.rsplit('_', 2)  # Split from right to handle cases with extra underscores
    if len(parts) < 2:
        raise ValueError(f"Invalid filename format: {name}. Expected format: timestamp_type.txt")
        
    file_type = parts[-1].split('.')[0]  # Get type between last underscore and .txt
    
    if file_type == 'changes':
        return 'changes'
    elif file_type == 'analysis':
        return 'analysis'
    elif file_type == 'selected':
        return 'selected'
    
    raise ValueError(f"Unknown file type: '{file_type}'. Expected: changes, analysis, or selected")