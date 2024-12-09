from pathlib import Path
from typing import Dict, Tuple, List, Optional, Union
from dataclasses import dataclass
import re
import ast
import sys
import os  # Add this import
from rich.console import Console
from rich.panel import Panel
from janito.config import config

def validate_file_path(filepath: Path) -> Tuple[bool, str]:
    """
    Validate that the file path exists and is readable
    
    Args:
        filepath: Path object to validate
        
    Returns:
        Tuple[bool, str]: (is_valid, error_message)
    """
    if not filepath.exists():
        return False, f"File does not exist: {filepath}"
    if not os.access(filepath, os.R_OK):
        return False, f"File is not readable: {filepath}"
    return True, ""

def validate_file_content(content: str) -> Tuple[bool, str]:
    """
    Validate that the content is not empty and contains valid text
    
    Args:
        content: String content to validate
        
    Returns:
        Tuple[bool, str]: (is_valid, error_message)
    """
    if not content:
        return False, "Content cannot be empty"
    if not isinstance(content, str):
        return False, "Content must be a string"
    return True, ""

@dataclass
class FileChange:
    """Represents a file change with search/replace, search/delete, create or replace instructions"""
    path: Path
    description: str
    is_new_file: bool
    content: str = ""  # For new files or replace operations
    original_content: str = ""  # Original content for file replacements
    search_blocks: List[Tuple[str, Optional[str], Optional[str]]] = None  # (search, replace, description)
    replace_file: bool = False  # Flag for complete file replacement
    remove_file: bool = False  # Flag for file deletion

    def add_search_block(self, search: str, replace: Optional[str], description: Optional[str] = None) -> None:
        """Add a search/replace or search/delete block with optional description"""
        if self.search_blocks is None:
            self.search_blocks = []
        self.search_blocks.append((search, replace, description))

@dataclass
class FileBlock:
    """Raw file block data extracted from response"""
    uuid: str
    filepath: str
    action: str
    description: str
    content: str

def validate_python_syntax(content: str, filepath: Path) -> Tuple[bool, str]:
    """Validate Python syntax and return (is_valid, error_message)"""
    try:
        ast.parse(content)
        console = Console()
        try:
            rel_path = filepath.relative_to(Path.cwd())
            display_path = f"./{rel_path}"
        except ValueError:
            display_path = str(filepath)
        console.print(f"[green]✓ Python syntax validation passed:[/green] {display_path}")
        return True, ""
    except SyntaxError as e:
        error_msg = f"Line {e.lineno}: {e.msg}"
        console = Console()
        try:
            rel_path = filepath.relative_to(Path.cwd())
            display_path = f"./{rel_path}"
        except ValueError:
            display_path = str(filepath)
        console.print(f"[red]✗ Python syntax validation failed:[/red] {display_path}")
        console.print(f"[red]  {error_msg}[/red]")
        return False, error_msg

def count_lines(text: str) -> int:
    """Count the number of lines in a text block."""
    return len(text.splitlines())

def extract_file_blocks(response_text: str) -> List[Tuple[str, str, str, str]]:
    """Extract file blocks from response text and return list of (uuid, filepath, action, description, content)"""
    file_blocks = []
    console = Console()
    
    # Find file blocks with improved quoted description handling
    file_start_pattern = r'## ([a-f0-9]{8}) file (.*?) (modify|create|remove|replace)(?:\s+"([^"]*?)")?\s*##'
    # Find the first UUID to check for duplicates
    first_match = re.search(file_start_pattern, response_text)
    if not first_match:
        console.print("[red]FATAL ERROR: No file blocks found in response[/red]")
        sys.exit(1)
    fist_uuid = first_match.group(1)
    
    # Find all file blocks
    for match in re.finditer(file_start_pattern, response_text):
        block_uuid, filepath, action, description = match.groups()
        
        # Show debug info for create actions
        if config.debug and action == 'create':
            console.print(f"[green]Found new file block:[/green] {filepath}")
            
        # Now find the complete block
        full_block_pattern = (
            f"## {block_uuid} file.*?##\n?"
            f"(.*?)"
            f"## {block_uuid} file end ##"
        )
        
        block_match = re.search(full_block_pattern, response_text[match.start():], re.DOTALL)
        if not block_match:
            # Show context around the incomplete block
            context_start = max(0, match.start() - 100)
            context_end = min(len(response_text), match.start() + 100)
            context = response_text[context_start:context_end]
            
            console.print(f"\n[red]FATAL ERROR: Found file start but no matching end for {filepath}[/red]")
            console.print("[red]Context around incomplete block:[/red]")
            console.print(Panel(context, title="Context", border_style="red"))
            sys.exit(1)
            
        content = block_match.group(1)
        # For new files, preserve the first newline if it exists
        if action == 'create' and content.startswith('\n'):
            content = content[1:]
            
        file_blocks.append((block_uuid, filepath.strip(), action, description or "", content))
        
        if config.debug:
            action_type = "Creating new file" if action == "create" else "Modifying file"
            console.print(f"[green]Found valid block:[/green] {action_type} {filepath}")
            console.print(f"[blue]Content length:[/blue] {len(content)} chars")
            
    return file_blocks

def extract_modification_blocks(uuid: str, content: str) -> List[Tuple[str, str, Optional[str], str]]:
    """Extract all modification blocks from content, returns list of (type, description, replace, search)"""
    blocks = []
    console = Console()
    
    # Find all modification blocks in sequence
    block_start = r'## ' + re.escape(uuid) + r' (search/replace|search/delete) "(.*?)" ##\n'
    current_pos = 0
    
    while True:
        # Find next block start
        start_match = re.search(block_start, content[current_pos:], re.DOTALL)
        if not start_match:
            break
            
        block_type, description = start_match.groups()
        block_start_pos = current_pos + start_match.end()
        
        # Find block end based on type
        if block_type == 'search/replace':
            replace_marker = f"## {uuid} replace with ##\n"
            end_marker = f"## {uuid}"
            
            # Find replace marker
            replace_pos = content.find(replace_marker, block_start_pos)
            if replace_pos == -1:
                # Show context around the incomplete block
                context_start = max(0, current_pos + start_match.start() - 100)
                context_end = min(len(content), current_pos + start_match.end() + 100)
                context = content[context_start:context_end]
                
                console.print(f"\n[red]FATAL ERROR: Missing 'replace with' marker for block:[/red] {description}")
                console.print("[red]Context around incomplete block:[/red]")
                console.print(Panel(context, title="Context", border_style="red"))
                sys.exit(1)
                
            # Get search content
            search = content[block_start_pos:replace_pos]
            
            # Find end of replacement
            replace_start = replace_pos + len(replace_marker)
            next_block = content.find(end_marker, replace_start)
            if next_block == -1:
                # Use rest of content if no end marker found
                replace = content[replace_start:]
            else:
                replace = content[replace_start:next_block]
            
            blocks.append(('replace', description, replace, search))
            current_pos = next_block if next_block != -1 else len(content)
            
        else:  # search/delete
            # Find either next block start or end of content
            next_block_marker = content.find(f"## {uuid}", block_start_pos)
            if next_block_marker == -1:
                # Use rest of content if no more blocks
                search = content[block_start_pos:]
            else:
                search = content[block_start_pos:next_block_marker]
                
            blocks.append(('delete', description, None, search))
            current_pos = next_block_marker if next_block_marker != -1 else len(content)
            
        if config.debug:
            console.print(f"[green]Found {block_type} block:[/green] {description}")
            
    return blocks

def handle_file_block(block: FileBlock) -> FileChange:
    """Process a single file block and return a FileChange object"""
    console = Console()
    
    # Handle file removal action
    if block.action == 'remove':
        return FileChange(
            path=Path(block.filepath),
            description=block.description,
            is_new_file=False,
            content="",
            search_blocks=[],
            remove_file=True
        )
    
    # Validate file path
    path = Path(block.filepath)
    is_valid, error = validate_file_path(path)
    if block.action == 'replace' and not is_valid:
        console.print(f"[red]Invalid file path for replacement:[/red] {error}")
        sys.exit(1)
    
    # Handle file replacement action
    if block.action == 'replace':
        # Read original content if file exists
        original_content = ""
        if path.exists():
            try:
                original_content = path.read_text()
            except Exception as e:
                console.print(f"[red]Error reading original file for replacement:[/red] {e}")
                sys.exit(1)
                
        return FileChange(
            path=Path(block.filepath),
            description=block.description,
            is_new_file=False,
            content=block.content.lstrip('\n'),
            original_content=original_content,
            search_blocks=[],
            replace_file=True
        )
    
    # Validate content for new files
    if block.action == 'create':
        is_valid, error = validate_file_content(block.content)
        if not is_valid:
            console.print(f"[red]Invalid file content for {block.filepath}:[/red] {error}")
            sys.exit(1)
    
    if block.action == 'create':
        return FileChange(
            path=Path(block.filepath),
            description=block.description,
            is_new_file=True,
            content=block.content[1:] if block.content.startswith('\n') else block.content,
            search_blocks=[]
        )
    
    # Extract and process modification blocks
    search_blocks = []
    for block_type, description, replace, search in extract_modification_blocks(block.uuid, block.content):
        # Ensure consistent line endings
        search = search.rstrip('\n') + '\n'
        if replace is not None:
            replace = replace.rstrip('\n') + '\n'
            
        if config.debug:
            console.print(f"\n[cyan]Processing {block_type} block:[/cyan] {description}")
            console.print(Panel(search, title="Search Content"))
            if replace:
                console.print(Panel(replace, title="Replace Content"))
                
        search_blocks.append((search, replace, description))
    
    return FileChange(
        path=Path(block.filepath),
        description=block.description,
        is_new_file=False,
        search_blocks=search_blocks
    )

def parse_block_changes(response_text: str) -> List[FileChange]:
    """Parse file changes from response blocks and return list of FileChange"""
    changes = []
    console = Console()
    
    # First extract all file blocks
    file_blocks = extract_file_blocks(response_text)
    
    # Process each file block independently
    for block_uuid, filepath, action, description, content in file_blocks:
        path = Path(filepath)
        
        file_block = FileBlock(
            uuid=block_uuid,
            filepath=filepath,
            action=action,
            description=description,
            content=content
        )
        
        file_change = handle_file_block(file_block)
        # For remove action, ensure remove_file flag is set
        if action == 'remove':
            file_change.remove_file = True
        file_change.path = path
        changes.append(file_change)

    if config.debug:
        console.print(f"\n[cyan]Processed {len(file_blocks)} file blocks[/cyan]")
        
    return changes