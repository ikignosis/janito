import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional
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

Create File
    Desc: <optional description>
    Path: <path>
    Content: 
        <content lines> (use . prefix and . suffix for each line)

Remove File
    Desc: <optional description>
    Path: <path>

Rename File
    Desc: <optional description>
    OldPath: <old_path>
    NewPath: <new_path>

Modify File
    Desc: <optional description>
    Path: <path>
    Modifications: 
        Select
            .<search content>.
        SelectRegex
            .<python re earch regex>.
        Replace Selected
            .<replace content>.
        Select
            .<search content>.                
        Delete Selected (will delete, prefer it for removing lines)

Replace File
    Desc: <optional description>
    Path: <path>
    Content: 
        <content lines> (use . prefix and . suffix for each line)

EXAMPLE:
Create File
    Desc: Add new function
    Path: new.py
    Content:
        .def new_function():.
        .   return True.


RULES:
- search content MUST preserve the original indentation/whitespace, while adding the . prefix and . suffix to each line. eg. .def test():.
- consider the effect of previous changes on new modifications (e.g. if a line is removed, it can't be modified later)
- ensure the file content is valid and complete after modifications
- use SearchRegex to reduce search content size when possible, but ensure it is accurate, otherwise use SearchText
- ensure the search content is unique to avoid unintended modifications
- do not provide any other feedback or instructions apart from change instructions
"""

@dataclass
class Modification:
    """Represents a search and replace/delete operation"""
    search_content: str
    replace_content: Optional[str] = None
    is_regex: bool = False

@dataclass
class FileChange:
    """Represents a file change operation"""
    operation: str
    path: Path
    new_path: Optional[Path] = None
    description: Optional[str] = None
    content: Optional[str] = None
    modifications: Optional[List[Modification]] = None
    original_content: Optional[str] = None  # For storing content before replacement

class CommandParser:
    def __init__(self, debug=False):
        self.debug = debug
        self.console = Console(stderr=True)
        self.current_line = 0
        self.lines = []

    def parse_response(self, input_text: str) -> List[FileChange]:
        if not input_text.strip():
            return []
        
        self.lines = [line.rstrip() for line in input_text.splitlines()]
        self.current_line = 0
        changes = []
        
        while self.current_line < len(self.lines):
            command = self.get_next_command()
            if command:
                if command in ['Create File', 'Replace File', 'Remove File', 'Rename File', 'Modify File']:
                    change = self.parse_file_command(command)
                    if change:
                        changes.append(change)
        return changes

    def get_next_command(self) -> Optional[str]:
        while self.current_line < len(self.lines):
            line = self.lines[self.current_line].strip()
            self.current_line += 1
            if line and not line.startswith('#') and ':' not in line and '.' not in line:
                return line
        return None

    def parse_file_command(self, command: str) -> Optional[FileChange]:
        change = FileChange(operation=command.lower().replace(' ', '_'), path=Path())
        
        while self.current_line < len(self.lines):
            line = self.lines[self.current_line].strip()
            if not line or line.startswith('#'):
                self.current_line += 1
                continue
            
            if ':' not in line and '.' not in line:
                break

            if ':' in line:
                key, value = [x.strip() for x in line.split(':', 1)]
                self.current_line += 1
                
                if key == 'Modifications':
                    change.modifications = self.parse_modifications()
                else:
                    self.handle_parameter(change, key, value)
                    
        return change

    def handle_parameter(self, change: FileChange, key: str, value: str):
        if key == 'Path':
            change.path = Path(value) if value else Path(self.get_text_block())
        elif key == 'NewPath':
            change.new_path = Path(value) if value else Path(self.get_text_block())
        elif key == 'OldPath':
            change.path = Path(value) if value else Path(self.get_text_block())
        elif key == 'Desc':
            change.description = value if value else self.get_text_block()
        elif key == 'Content':
            change.content = value if value else self.get_text_block()

    def get_text_block(self) -> str:
        lines = []
        while self.current_line < len(self.lines):
            line = self.lines[self.current_line].strip()
            if not line.startswith('.'):
                break
            if not line.endswith('.'):
                raise ValueError(f"Text block line missing trailing dot: {line}")
            lines.append(line[1:-1])
            self.current_line += 1
        return '\n'.join(lines)

    def parse_modifications(self) -> List[Modification]:
        modifications = []
        while self.current_line < len(self.lines):
            line = self.lines[self.current_line].strip()
            if not line or line.startswith('#'):
                self.current_line += 1
                continue
                
            # Stop if we hit a line that doesn't look like part of the modifications block
            if not line.startswith(('Select', 'SelectRegex')) and ':' not in line and '.' not in line:
                break
                
            if line.startswith(('Select', 'SelectRegex')):
                is_regex = line.startswith('SelectRegex')
                self.current_line += 1
                search_content = self.get_text_block()
                
                # Get the next command (Replace/Delete)
                while self.current_line < len(self.lines):
                    line = self.lines[self.current_line].strip()
                    if not line or line.startswith('#'):
                        self.current_line += 1
                        continue
                    break
                
                if not line:  # EOF
                    break
                    
                self.current_line += 1
                
                if line.startswith(('Delete Selected', 'Delete')):
                    modifications.append(Modification(search_content=search_content, is_regex=is_regex))
                elif line.startswith(('Replace Selected', 'Replace')):
                    replace_content = self.get_text_block()
                    modifications.append(Modification(
                        search_content=search_content,
                        replace_content=replace_content,
                        is_regex=is_regex
                    ))
            else:
                self.current_line += 1
                    
        return modifications

def parse_response(response_text: str) -> List[FileChange]:
    """Compatibility wrapper for existing code"""
    parser = CommandParser(debug=config.debug)
    return parser.parse_response(response_text)

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