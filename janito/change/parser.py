import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple, Optional
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from janito.config import config

console = Console(stderr=True)

CHANGE_REQUEST_PROMPT = """
Original request: {request}

Please provide detailed implementation using the following guide:
{option_text}

Current files:
<files>
{files_content}
</files>

RULES for analysis:
- When removing constants, ensure they are not used elsewhere
- When adding new features to python files, add the necessary imports
- Python imports should be inserted at the top of the file
- For complete file replacements, only use for existing files marked as modified
- File replacements must preserve the essential functionality

Please provide the changes I should apply in the following format:

In order to differentiate content from instructions, prefix all content lines with an extra dot (.) .
Non dotted lines will be considered as instructions, content must be terminate with a blank line.
I understand the following changes will be applied to the files listed above:

Create file
    Desc: <optional description>
    Path: <filepath>
    Content: (dotted content starting below)

Replace file
    Desc: <optional description>
    Path: <filepath>
    Content: (dotted content starting below)

Remove file
    Desc: <optional description>
    Path: <filepath>

Rename file
    Desc: <optional description>
    OldPath: <old_filepath>
    Newpath: <new_filepath>

Modify file
    Desc: <optional description>
    Path: <filepath>
    Actions:
        SearchText or SearchRegex (original search content provided below, text or regex)
<search_content>
        Replace
<new_content>
        Delete (delete previous searched content)
        ... provide more search/replace/delete actions as needed ...

... provide more file operations as needed ...

RULES:
1. search content MUST preserve the original indentation/whitespace, while adding the . prefix
2. consider the effect of previous changes on new modifications (e.g. if a line is removed, it can't be modified later)
3. if modifications to a file are too big, consider a file replacement instead
4. ensure the file content is valid and complete after modifications
5. use SearchRegex to reduce search content size when possible, but ensure it is accurate, otherwise use SearchText
6. ensure the search content is unique to avoid unintended modifications
7. do not provide any other feedback or instructions apart from change instructions
"""

@dataclass
class Modification:
    """Represents a search and replace/delete operation"""
    search_type: str  # 'SearchText' or 'SearchRegex'
    search_content: str
    search_display_content: str  # The content as located in the original file (for display, eg. result from regex search)
    replace_content: Optional[str]  # None for delete operations

@dataclass
class FileChange:
    """Represents a file change operation"""
    operation: str  # 'create', 'replace', 'remove', 'rename', 'modify'
    description: str
    filepath: Path
    new_filepath: Optional[Path]  # Only for rename operations
    content: Optional[str]  # For create/replace operations
    modifications: List[Modification]  # For modify operations
    original_content: Optional[str] = None  # For storing original content in replace operations

def parse_dotted_content(lines: List[str], start_idx: int) -> tuple[int, str]:
    """Parse content lines starting with dots, returns (next_line_idx, content)"""
    if config.debug:
        console.print(f"[yellow]Parsing dotted content starting at line {start_idx}[/]")
        
    content_lines = []
    idx = start_idx
    while idx < len(lines) and lines[idx].startswith('.'):
        content_lines.append(lines[idx][1:])  # Remove the dot
        idx += 1
        
    if config.debug and content_lines:
        console.print("[dim]Found dotted content:[/]")
        console.print(Syntax('\n'.join(content_lines), "python", background_color="default"))
        
    return idx, '\n'.join(content_lines)

def parse_modification(lines: List[str], start_idx: int) -> tuple[int, Optional[Modification]]:
    if config.debug:
        console.print(f"\n[yellow]Parsing modification at line {start_idx}[/]")
        
    if start_idx >= len(lines):
        if config.debug:
            console.print("[red]End of lines reached[/]")
        return start_idx, None
        
    line = lines[start_idx].strip()
    if not line or not (line.startswith('SearchText') or line.startswith('SearchRegex')):
        return start_idx, None
        
    search_type = 'SearchText' if line.startswith('SearchText') else 'SearchRegex'
    idx = start_idx + 1
    
    # Parse search content
    idx, search_content = parse_dotted_content(lines, idx)
    
    if idx >= len(lines):
        raise ValueError("Incomplete modification block")
        
    action = lines[idx].strip()
    idx += 1
    
    # Parse replace content if not delete
    replace_content = None
    if action == 'Replace':
        idx, replace_content = parse_dotted_content(lines, idx)
    elif action != 'Delete':
        raise ValueError(f"Invalid action: {action}")
    
    if config.debug:
        console.print(f"[green]Found {search_type} operation[/]")
        if replace_content is not None:
            console.print("[dim]With replacement content[/]")
    
    return idx, Modification(
        search_type=search_type,
        search_content=search_content,
        search_display_content=search_content,
        replace_content=replace_content
    )

def parse_modify_operations(lines: List[str], start_idx: int) -> tuple[int, List[Modification]]:
    """Parse modification operations, returns (next_line_idx, modifications)"""
    modifications = []
    idx = start_idx
    
    while idx < len(lines):
        next_idx, modification = parse_modification(lines, idx)
        if modification is None:
            break
        modifications.append(modification)
        idx = next_idx
    
    return idx, modifications

def parse_response(response_text: str) -> List[FileChange]:
    if config.debug:
        console.print("\n[yellow]Starting response parsing[/]")
        
    lines = response_text.split('\n')
    changes = []
    idx = 0
    
    while idx < len(lines):
        line = lines[idx].strip()
        
        if not line.startswith(('Create file', 'Replace file', 'Remove file', 'Rename file', 'Modify file')):
            idx += 1
            continue
            
        if config.debug:
            console.print(f"\n[blue]Processing {line}[/]")
            
        operation = line.lower().split()[0]
        
        # Parse common fields
        desc = ''
        filepath = None
        new_filepath = None
        content = None
        modifications = []
        
        idx += 1
        while idx < len(lines) and (lines[idx].strip().startswith(('Desc:', 'Path:', 'NewPath:', 'Content:', 'Actions:'))):
            line = lines[idx].strip()
            if config.debug:
                console.print(f"[dim]Processing line: {line}[/]")
            
            try:
                if ':' not in line:
                    if config.debug:
                        console.print(f"[red]Invalid line format (missing colon): {line}[/]")
                    idx += 1
                    continue
                    
                key, value = [x.strip() for x in line.split(':', 1)]
                
                if config.debug:
                    console.print(f"[dim]Key: '{key}', Value: '{value}'[/]")
                
                if key == 'Desc':
                    desc = value
                elif key == 'Path':
                    filepath = Path(value)
                elif key == 'NewPath':
                    new_filepath = Path(value)
                elif key == 'Content':
                    idx += 1
                    idx, content = parse_dotted_content(lines, idx)
                    continue
                elif key == 'Actions':
                    idx += 1
                    idx, modifications = parse_modify_operations(lines, idx)
                    continue
                
            except Exception as e:
                if config.debug:
                    console.print(f"[red]Error processing line {idx}: {str(e)}[/]")
                    console.print(f"[red]Line content: {line}[/]")
            
            idx += 1
        
        if config.debug:
            console.print(f"[green]Added {operation} change for {filepath}[/]")
            
        changes.append(FileChange(
            operation=operation,
            description=desc,
            filepath=filepath,
            new_filepath=new_filepath,
            content=content,
            modifications=modifications
        ))
        
    if config.debug:
        console.print(f"\n[green]Parsing complete. Found {len(changes)} changes.[/]")
        
    return changes

def build_change_request_prompt(option_text: str, request: str, files_content: str = "") -> str:
    """Build prompt for change request details
    
    Args:
        option_text: Formatted text describing the selected option
        request: The original user request
        files_content: Content of relevant files
    """
    short_uuid = str(uuid.uuid4())[:8]
    
    return CHANGE_REQUEST_PROMPT.format(
        option_text=option_text,
        request=request,
        files_content=files_content,
        uuid=short_uuid
    )