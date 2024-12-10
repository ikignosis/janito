import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple, Optional
from rich.console import Console
from rich.panel import Panel
from janito.config import config

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

Create file:
    Desc: <optional description>
    Path: <filepath>
    Content: (dotted content starting below)

Replace file:
    Desc: <optional description>
    Path: <filepath>
    Content: (dotted content starting below)

Remove file:
    Desc: <optional description>
    Path: <filepath>

Rename file:
    Desc: <optional description>
    OldPath: <old_filepath>
    Newpath: <new_filepath>

Modify file:
    Desc: <optional description>
    Path: <filepath>
    Operations:
        SearchText or SearchRegex: (original search content provided below, text or regex)
<search content>
        Replace:
<new_content>
        Delete (deleted previous searched content)
        ... provide more search/replace or search/delete operations as needed ...

RULES:
1. search content MUST preserve the original indentation/whitespace
2. consider the effect of previous changes on new modifications (e.g. if a line is removed, it can't be modified later)
3. if modifications to a file are too big, consider a file replacement instead
4. ensure the file content is valid and complete after modifications
5. use SearchRegex to reduce search content size when possible, but ensure it is accurate, otherwise use SearchText
6. ensure the search content is unique to avoid unintended modifications
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

def parse_dotted_content(lines: List[str], start_idx: int) -> tuple[int, str]:
    """Parse content lines starting with dots, returns (next_line_idx, content)"""
    content_lines = []
    idx = start_idx
    while idx < len(lines) and lines[idx].startswith('.'):
        content_lines.append(lines[idx][1:])  # Remove the dot
        idx += 1
    return idx, '\n'.join(content_lines)

def parse_modify_operations(lines: List[str], start_idx: int) -> tuple[int, List[Modification]]:
    """Parse modification operations, returns (next_line_idx, modifications)"""
    modifications = []
    idx = start_idx
    
    while idx < len(lines):
        line = lines[idx].strip()
        if not line or not line.startswith('SearchText') and not line.startswith('SearchRegex'):
            break
            
        search_type = 'SearchText' if line.startswith('SearchText') else 'SearchRegex'
        idx += 1
        
        # Parse search content
        search_start = idx
        while idx < len(lines) and not lines[idx].strip() == 'Replace:' and not lines[idx].strip() == 'Delete':
            idx += 1
        if idx >= len(lines):
            raise ValueError("Incomplete modification block")
            
        search_content = '\n'.join(lines[search_start:idx])
        action = lines[idx].strip()
        idx += 1
        
        # Parse replace content if not delete
        replace_content = None
        if action == 'Replace:':
            replace_start = idx
            while idx < len(lines) and lines[idx].strip():
                idx += 1
            replace_content = '\n'.join(lines[replace_start:idx])
        
        modifications.append(Modification(search_type, search_content, replace_content))
        idx += 1
    
    return idx, modifications

def parse_response(response_text: str) -> List[FileChange]:
    """Parse the response text and return list of FileChange objects"""
    lines = response_text.split('\n')
    changes = []
    idx = 0
    
    while idx < len(lines):
        line = lines[idx].strip()
        
        if line.startswith(('Create file:', 'Replace file:', 'Remove file:', 'Rename file:', 'Modify file:')):
            operation = line.split(':')[0].lower().split()[0]  # get 'create', 'replace', etc.
            
            # Parse common fields
            desc = ''
            filepath = None
            new_filepath = None
            content = None
            modifications = []
            
            idx += 1
            while idx < len(lines) and lines[idx].strip():
                key, value = [x.strip() for x in lines[idx].split(':', 1)]
                
                if key == 'Desc':
                    desc = value
                elif key == 'Path':
                    filepath = Path(value)
                elif key == 'OldPath':
                    filepath = Path(value)
                elif key == 'NewPath':
                    new_filepath = Path(value)
                elif key == 'Content':
                    idx += 1
                    idx, content = parse_dotted_content(lines, idx)
                    continue
                elif key == 'Operations':
                    idx += 1
                    idx, modifications = parse_modify_operations(lines, idx)
                    continue
                
                idx += 1
            
            changes.append(FileChange(
                operation=operation,
                description=desc,
                filepath=filepath,
                new_filepath=new_filepath,
                content=content,
                modifications=modifications
            ))
        else:
            idx += 1
    
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