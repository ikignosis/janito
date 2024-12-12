import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional
from rich.console import Console
from janito.config import config
from janito.ssfparser.ssfparser import SSFParser, StatementContext, Section, Line, LineType

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
- When including text for selection, keep the original text intact

Please provide me the changes instructions using the following format:

Create File
    Path:file.py
    /Content
    .def new_function():
    .    return True
    Content/

Remove File
    Path: file.py

Rename File
    OldPath: old.py
    NewPath: new.py

Modify File
    Path: file.py
    /Modifications
        /replace
            /text
                .def old_function():
                .    return "old"
            text/
            /with
                .def new_function():
                .    return "new"        
            with/
        replace/
        /delete
            /text
                .def to_be_deleted():
                .    pass
            text/
        delete/
    Modifications/

RULES:
- content MUST preserve the original indentation/whitespace
- use . as prefix for text block lines
- ensure search content is unique to avoid unintended modifications
- do not provide any other feedback or instructions after the change instructions
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
        self.ssf_parser = SSFParser()

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

        parsed_items = self.ssf_parser.parse(input_text)
        changes = []

        for item in parsed_items:
            if not isinstance(item, dict) or item.get('type') != 'statement':
                continue
            
            if item['name'] in ['Create File', 'Replace File', 'Remove File', 'Rename File', 'Modify File']:
                change = self.convert_statement_to_filechange(item)
                if change:
                    changes.append(change)

        if self.debug:
            self.console.print(f"[dim]Finished parsing, found {len(changes)} changes[/dim]")
        return changes

    def convert_statement_to_filechange(self, statement: dict) -> Optional[FileChange]:
        """Convert a SSF Statement to a FileChange object"""
        if not statement.get('parameters'):
            return None

        change = FileChange(
            operation=statement['name'].lower().replace(' ', '_'),
            path=Path()
        )

        # Handle parameters
        for key, value in statement['parameters'].items():
            if key == 'Path':
                change.path = Path(value)
            elif key == 'NewPath':
                change.new_path = Path(value)
            elif key == 'OldPath':
                change.path = Path(value)
            elif key == 'Desc':
                change.description = value

        # Handle sections
        if 'Content' in statement.get('sections', {}):
            content_section = statement['sections']['Content']
            change.content = content_section.get_text_content()

        if 'Modifications' in statement.get('sections', {}):
            mods_section = statement['sections']['Modifications']
            change.modifications = self.parse_modifications_from_list(mods_section.content)

        return change

    def parse_modifications_from_list(self, mod_list: list) -> List[Modification]:
        """Convert SSF parsed modifications list to Modification objects"""
        modifications = []

        for item in mod_list:
            if not isinstance(item, Section):
                continue
                
            if item.name == 'replace':
                text_section = next((s for s in item.content if isinstance(s, Section) and s.name == 'text'), None)
                with_section = next((s for s in item.content if isinstance(s, Section) and s.name == 'with'), None)
                
                if text_section and with_section:
                    modifications.append(Modification(
                        search_content=text_section.get_text_content(),
                        replace_content=with_section.get_text_content()
                    ))
            elif item.name == 'delete':
                text_section = next((s for s in item.content if isinstance(s, Section) and s.name == 'text'), None)
                if text_section:
                    modifications.append(Modification(search_content=text_section.get_text_content()))

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