import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional
from rich.console import Console
from janito.config import config
from janito.clear_statement_parser.parser import Statement, StatementParser

console = Console(stderr=True)

from .prompts import CHANGE_REQUEST_PROMPT


import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Dict, Union
from rich.console import Console
from enum import Enum, auto

class ChangeOperation(Enum):
    CREATE_FILE = auto()
    REPLACE_FILE = auto()
    RENAME_FILE = auto()
    REMOVE_FILE = auto()
    MODIFY_FILE = auto()
    MOVE_FILE = auto()

@dataclass
class TextChange:
    """Represents a search and replace/delete operation"""
    search_content: Optional[str] = None
    replace_content: Optional[str] = None
    reason: Optional[str] = None
    operation: Optional[str] = None

    @property
    def is_append(self) -> bool:
        return self.operation == 'Append'

    @property
    def is_delete(self) -> bool:
        return self.operation == 'Delete' or (self.search_content and not self.replace_content)
    
    def validate(self) -> bool:
        """Validate the text change operation"""
        if not self.search_content and self.replace_content is None:
            return False
        return True

@dataclass
class FileChange:
    """Represents a file change operation"""
    operation: ChangeOperation
    name: Path  # Changed back from path to name
    target: Optional[Path] = None
    source: Optional[Path] = None
    content: Optional[str] = None
    text_changes: List[TextChange] = field(default_factory=list)
    original_content: Optional[str] = None
    reason: Optional[str] = None

    def add_text_changes(self, changes: List[TextChange]):
        """Add multiple text changes to the existing list"""
        self.text_changes.extend(changes)

    @classmethod
    def from_dict(cls, data: Dict[str, Union[str, Path]]) -> 'FileChange':
        """Create FileChange instance from dictionary data"""
        operation = ChangeOperation[data['operation'].upper()]
        return cls(
            operation=operation,
            name=Path(data['name']),  # Changed back to name
            target=Path(data['target']) if data.get('target') else None,
            source=Path(data.get('source')) if data.get('source') else None,
            content=data.get('content'),
            reason=data.get('reason')
        )

    def validate_required_parameters(self) -> bool:
        """Validate the file change operation and raise detailed errors if parameters are missing"""
        if self.operation == ChangeOperation.RENAME_FILE:
            if not self.source:
                raise ValueError(f"Missing 'source' parameter for {self.operation.name}")
            if not self.target:
                raise ValueError(f"Missing 'target' parameter for {self.operation.name}")
                
        elif self.operation in (ChangeOperation.CREATE_FILE, ChangeOperation.REPLACE_FILE):
            if not self.content:
                raise ValueError(f"Missing 'content' parameter for {self.operation.name}")
                
        elif self.operation == ChangeOperation.MODIFY_FILE:
            if not self.text_changes:
                raise ValueError(f"No closed text changes found for {self.operation.name}")
                
        return True

class CommandParser:
    def __init__(self, debug: bool = False):
        self.debug = debug
        self.console = Console(stderr=True)
        
    def parse_statements(self, statements: List[Statement]) -> List[FileChange]:
        """Parse a list of Statement objects into FileChange objects"""
        if self.debug:
            self.console.print("[dim]Starting to parse statements...[/dim]")
            
        changes = []

        for statement in statements:
            statement_key = statement.name.upper().replace(' ', '_') 
            supported_opers = [op.name.title().upper() for op in ChangeOperation]
            if statement_key not in supported_opers: 
                raise Exception(f"{statement_key} not in supported statements: {supported_opers}")
                
            change = self.convert_statement_to_filechange(statement)
            if not change:
                raise Exception(f"Invalid change found: {statement.name}")
            if not change.validate_required_parameters():
                raise Exception(f"Missing required parameters for change: {statement.name}")
            changes.append(change)
        return changes

    def convert_statement_to_filechange(self, statement: Statement) -> Optional[FileChange]:
        """Convert a Statement to a FileChange object"""
        try:
            operation = ChangeOperation[statement.name.upper().replace(' ', '_')]
            change = FileChange(
                operation=operation,
                name=Path(statement.parameters.get('name', '')),  # Changed back to name
                reason=statement.parameters.get('reason')
            )

            if 'target' in statement.parameters:
                change.target = Path(statement.parameters['target'])
            if 'source' in statement.parameters:
                change.source = Path(statement.parameters['source'])
                change.name = Path(statement.parameters['source'])  # Changed back to name

            content = statement.parameters.get('content')
            if content:
                change.content = self._clean_content(content)

            # Handle multiple Changes blocks - combine all text changes
            all_text_changes = []
            for block_name, block_statements in statement.blocks:
                # Handle both numbered (Changes#1) and unnumbered (Changes) blocks
                base_name = block_name.split('#')[0]
                if base_name == 'Changes':
                    if self.debug:
                        self.console.print(f"[dim]Processing Changes block: {block_name}[/dim]")
                    new_changes = self.parse_modifications_from_list(block_statements)
                    all_text_changes.extend(new_changes)

            if all_text_changes:
                change.text_changes = all_text_changes

            return change
        except Exception as e:
            if self.debug:
                self.console.print(f"[red]Error converting statement: {e}[/red]")
            return None

    def parse_modifications_from_list(self, mod_statements: List[Statement]) -> List[TextChange]:
        """Convert parsed modifications list to TextChange objects"""
        modifications = []

        for statement in mod_statements:
            try:
                if statement.name == 'Replace':
                    mod = TextChange(
                        search_content=self._clean_content(statement.parameters.get('search', '')),
                        replace_content=self._clean_content(statement.parameters.get('with', '')),
                        reason=statement.parameters.get('reason'),
                        operation='Replace'
                    )
                elif statement.name == 'Delete':
                    mod = TextChange(
                        search_content=self._clean_content(statement.parameters.get('search', '')),
                        reason=statement.parameters.get('reason'),
                        operation='Delete'
                    )
                elif statement.name == 'Append':
                    mod = TextChange(
                        search_content='',
                        replace_content=self._clean_content(statement.parameters.get('content', '')),
                        reason=statement.parameters.get('reason'),
                        operation='Append'
                    )
                else:
                    continue

                if mod.validate():
                    modifications.append(mod)
            except Exception as e:
                if self.debug:
                    self.console.print(f"[red]Error processing modification: {e}[/red]")
                continue

        return modifications

    @staticmethod
    def _clean_content(content: str) -> str:
        """Clean content by removing leading dots and normalizing line endings"""
        if not content:
            return ''
        lines = content.splitlines()
        cleaned_lines = [line[1:] if line.startswith('.') else line for line in lines]
        return '\n'.join(cleaned_lines)

def extract_instructions_section(response_text: str) -> Optional[str]:
    """Extract text between BEGIN_INSTRUCTIONS and END_INSTRUCTIONS markers using exact line matching"""
    try:
        lines = response_text.splitlines()
        start_marker = "BEGIN_INSTRUCTIONS"
        end_marker = "END_INSTRUCTIONS"
        
        # Find exact line matches for markers
        start_idx = None
        end_idx = None
        
        for i, line in enumerate(lines):
            line = line.strip()
            if line == start_marker and start_idx is None:
                start_idx = i
                continue
            if line == end_marker and start_idx is not None:
                end_idx = i
                break
                
        if start_idx is None or end_idx is None:
            if config.debug:
                if start_idx is None:
                    console.print("[yellow]BEGIN_CHANGES marker not found[/yellow]")
                else:
                    console.print("[yellow]END_CHANGES marker not found[/yellow]")
            return None
            
        # Extract lines between markers (exclusive)
        changes_text = '\n'.join(lines[start_idx + 1:end_idx])
        if not changes_text.strip():
            if config.debug:
                console.print("[yellow]Empty changes section found[/yellow]")
            return None
            
        return changes_text.strip()
        
    except Exception as e:
        console.print(f"[red]Error extracting changes section: {e}[/red]")
        return None

def parse_response(response_text: str) -> List[FileChange]:
    """Parse a response string into FileChange objects"""
    parser = CommandParser()
    statement_parser = StatementParser()

    statements = statement_parser.parse(response_text)
    return parser.parse_statements(statements)

def build_change_request_prompt(
    option_text: str,
    request: str,
) -> str:
    """Build prompt for change request details
    
    Args:
        option_text: Formatted text describing the selected option
        request: The original user request
        files_content_xml: Content of relevant files in XML format
    
    Returns:
        Formatted prompt string
    """
    short_uuid = str(uuid.uuid4())[:8]
    
    return CHANGE_REQUEST_PROMPT.format(
        option_text=option_text,
        request=request,
        uuid=short_uuid
    )