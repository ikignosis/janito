import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional
from rich.console import Console
from janito.config import config
from janito.clear_statement_parser.csfparser import parse_clear_statement_format, Statement

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
- When including text from the original, keep the original text intact

Flow:
1. Analyze the changes required
2. Translate the changes into a set of instructions (format provided below)

Please provide me the changes instructions using the following format:

# Start of instructions
Create File
    name: hello_world.py
    content:
    .# This is a simple Python script
    .def greet():
    .    print("Hello, World!")

Remove File
    name: obsolete_script.py

Rename File
    source: old_name.txt
    target: new_name.txt

Modify File
    name: script.py
    /Changes
        Replace
            search:
            .def old_function():
            .    print("Deprecated")
            with:
            .def new_function():
            .    print("Updated")
        Delete
            search:
            .# This comment should be removed.
        # Append to the end of the file
        Append
            content:
            .# End of script
    Changes/

Replace File
    name: script.py
    target: scripts/script.py
    content:
    .# Updated Python script
    .def greet():
    .    print("Hello, World!")

# End of instructions

RULES:
- content MUST preserve the original indentation/whitespace
- use . as prefix for text block lines
- ensure search content is unique to avoid unintended modifications
- do not provide any other feedback or instructions after the change instructions
"""

@dataclass
class TextChange:
    """Represents a search and replace/delete operation"""
    search_content: str
    replace_content: Optional[str] = None

@dataclass
class FileChange:
    """Represents a file change operation"""
    operation: str
    name: Path  # Changed from path
    target: Optional[Path] = None 
    source: Optional[Path] = None 
    description: Optional[str] = None
    content: Optional[str] = None
    text_changes: Optional[List[TextChange]] = None
    original_content: Optional[str] = None

class CommandParser:
    def __init__(self, debug=False):
        self.debug = debug
        self.console = Console(stderr=True)

    def format_with_line_numbers(self, content: str) -> str:
        """Format content with line numbers for debug output."""
        lines = content.splitlines()
        max_line_width = len(str(len(lines)))
        return '\n'.join(f"{i+1:>{max_line_width}}: {line}" for i, line in enumerate(lines))

    def parse_response(self, input_text: str) -> List[FileChange]:
        if self.debug:
            self.console.print("[dim]Starting to parse response...[/dim]")
            
        if not input_text.strip():
            return []

        statements = parse_clear_statement_format(input_text, strict_mode=False)
        changes = []

        for statement in statements:
            if statement.content in ['Create File', 'Replace File', 'Remove File', 'Rename File', 'Modify File']:
                change = self.convert_statement_to_filechange(statement)
                if change:
                    changes.append(change)

        if self.debug:
            self.console.print(f"[dim]Finished parsing, found {len(changes)} changes[/dim]")
        return changes

    def convert_statement_to_filechange(self, statement: Statement) -> Optional[FileChange]:
        """Convert a CSF Statement to a FileChange object"""
        if not statement.parameters:
            return None

        # Handle single file operations
        change = FileChange(
            operation=statement.content.lower().replace(' ', '_'),
            name=Path()
        )

        # Handle parameters
        for key, value in statement.parameters.items():
            if key.lower() == 'name':
                change.name = Path(value)
            elif key.lower() == 'target':
                change.target = Path(value)
            elif key.lower() == 'source':
                change.source = Path(value)
                change.name = Path(value)
            elif key.lower() == 'description':
                change.description = value
            elif key.lower() == 'content':
                change.content = value

        # Handle blocks
        if 'content' in statement.blocks:
            content_block = statement.blocks['content']
            if content_block and len(content_block) > 0:
                change.content = content_block[0].content

        if 'Changes' in statement.blocks:
            mods_block = statement.blocks['Changes']
            change.text_changes = self.parse_modifications_from_list(mods_block)
    
        return change

    def parse_modifications_from_list(self, mod_statements: List[Statement]) -> List[TextChange]:
        """Convert CSF parsed modifications list to Modification objects"""
        modifications = []

        for statement in mod_statements:
            if statement.content == 'Replace':
                search_content = statement.parameters.get('search', '')
                replace_content = statement.parameters.get('with', '')
                modifications.append(TextChange(
                    search_content=search_content,
                    replace_content=replace_content
                ))
            elif statement.content == 'Delete':
                search_content = statement.parameters.get('search', '')
                modifications.append(TextChange(search_content=search_content))
            elif statement.content == 'Append':
                content = statement.parameters.get('content', '')
                modifications.append(TextChange(
                    search_content='',  # Empty search means append
                    replace_content=content
                ))

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