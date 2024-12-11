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
        .def new_function():
        .    return True

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
            .def old_function():
            .    return "old"
        Replace
            .def new_function():
            .    return "new"        
        Select
            .def to_be_deleted():
            .    pass
        Delete

RULES:
- content MUST preserve the original indentation/whitespace
- use . as prefix for text block lines
- consider the effect of previous changes on new modifications (e.g. if a line is removed, it can't be modified later)
- ensure the file content is valid and complete after modifications
- use SearchRegex to reduce search content size when possible, but ensure it is accurate, otherwise use SearchText
- ensure the search content is unique to avoid unintended modifications
- do not provide any other feedback or instructions after the change instructions
- comments are allowed with #, but only at the start of the line
    * comments are ignored during processing but should be provided for context
    * in the Select commands, comments SHOULD be added to identify the position of the text block in the original files (line number)
"""

@dataclass
class Modification:
    """Represents a search and replace/delete operation"""
    search_content: str
    replace_content: Optional[str] = None

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

    def format_with_line_numbers(self, content: str) -> str:
        """Format content with line numbers for debug output."""
        lines = content.splitlines()
        max_line_width = len(str(len(lines)))
        return '\n'.join(f"{i+1:>{max_line_width}}: {line}" for i, line in enumerate(lines))

    def parse_response(self, input_text: str) -> List[FileChange]:
        if self.debug:
            self.console.print("[dim]Starting to parse response...[/dim]")
            self.console.print(f"[dim]Total lines to process: {len(input_text.splitlines())}[/dim]")
            self.console.print("[dim]Content to parse:[/dim]")
            self.console.print(self.format_with_line_numbers(input_text))
            
        if not input_text.strip():
            return []
        
        # left strip each line to remove leading whitespace
        self.lines = [line.lstrip() for line in input_text.splitlines()]
        self.current_line = 0
        changes = []
        
        while self.current_line < len(self.lines):
            command = self.get_next_command()
            if command:
                if self.debug:
                    self.console.print(f"[dim]Processing command: {command}[/dim]")
                if command in ['Create File', 'Replace File', 'Remove File', 'Rename File', 'Modify File']:
                    change = self.parse_file_command(command)
                    if change:
                        changes.append(change)

        if self.debug:
            self.console.print(f"[dim]Finished parsing, found {len(changes)} changes[/dim]")
        return changes

    def get_next_command(self) -> Optional[str]:
        while self.current_line < len(self.lines):
            line = self.lines[self.current_line].strip()
            if self.debug:
                self.console.print(f"[dim]Line {self.current_line + 1}: Looking for command in: {line}[/dim]")
            self.current_line += 1
            if line and not line.startswith('#') and ':' not in line and '.' not in line:
                return line
        return None

    def parse_file_command(self, command: str) -> Optional[FileChange]:
        if self.debug:
            self.console.print(f"[dim]Parsing file command: {command} at line {self.current_line}[/dim]")
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
        if self.debug:
            self.console.print(f"[dim]Reading text block starting at line {self.current_line}[/dim]")
        lines = []
        while self.current_line < len(self.lines):
            line = self.lines[self.current_line].lstrip()
            if not line or line.startswith('#'):
                self.current_line += 1
                continue
            if not line.startswith('.'):
                break            
            # Remove only the first dot, preserving all whitespace
            lines.append(line[1:])
            self.current_line += 1
        return '\n'.join(lines) + '\n'

    def parse_modifications(self) -> List[Modification]:
        if self.debug:
            self.console.print(f"[dim]Starting to parse modifications at line {self.current_line}[/dim]")
        modifications = []
        while self.current_line < len(self.lines):
            line = self.lines[self.current_line].strip()
            if self.debug:
                self.console.print(f"[dim]Processing modification line {self.current_line}: {line}[/dim]")
            if not line or line.startswith('#'):
                self.current_line += 1
                continue
                
            # Stop if we hit a line that doesn't look like part of the modifications block
            if not line.startswith('Select') and ':' not in line and '.' not in line:
                break
                
            if line.startswith('Select'):
                self.current_line += 1
                search_content = self.get_text_block()
                #print(f"Search content: {search_content}")
                #for line in search_content.splitlines():
                #    print(repr(line))
                #exit(0)
                
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
                    modifications.append(Modification(search_content=search_content))
                elif line.startswith(('Replace Selected', 'Replace')):
                    replace_content = self.get_text_block()
                    modifications.append(Modification(
                        search_content=search_content,
                        replace_content=replace_content
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