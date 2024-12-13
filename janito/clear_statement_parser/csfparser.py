from dataclasses import dataclass
from typing import Dict, List, Union, Optional
from enum import Enum, auto

class LineType(Enum):
    EMPTY = auto()
    COMMENT = auto()
    STATEMENT = auto()
    LIST_ITEM = auto()
    TEXT_BLOCK = auto()
    KEY_VALUE = auto()
    BLOCK_START = auto()
    BLOCK_END = auto()
    BLOCK_CONTENT = auto()

@dataclass
class ParserError:
    line_number: int
    message: str
    context: str

    def __str__(self):
        return f"Line {self.line_number}: {self.message}\nContext: {self.context}"

class Statement:
    def __init__(self, content: str, line_number: int):
        self.content = content
        self.line_number = line_number
        self.parameters: Dict[str, Union[str, List, Dict]] = {}
        self.blocks: Dict[str, List[Statement]] = {}

    def __str__(self):
        return f"Statement(content='{self.content}', parameters={self.parameters}, blocks={self.blocks})"

    def __repr__(self):
        params_str = '\n'.join(f"      {k}: {repr(v)}" for k, v in self.parameters.items())
        blocks_str = '\n'.join(
            f"      {block_name}: [\n" + 
            '\n'.join(f"        {repr(stmt)}" for stmt in block_stmts) +
            "\n      ]"
            for block_name, block_stmts in self.blocks.items()
        )
        
        result = [f"Statement(line={self.line_number}, content='{self.content}')"]
        if self.parameters:
            result.append("  Parameters:")
            result.append(params_str)
        if self.blocks:
            result.append("  Blocks:")
            result.append(blocks_str)
        return '\n'.join(result)

class ClearStatementParser:
    def __init__(self, strict_mode: bool = True):
        self.strict_mode = strict_mode
        self.errors: List[ParserError] = []
        self.current_line = 0
        self.current_statement: Optional[Statement] = None
        self.parent_statement: Optional[Statement] = None
        self.current_key: Optional[str] = None
        self.current_block: Optional[str] = None
        self.statements: List[Statement] = []
        
    def parse(self, content: str) -> List[Statement]:
        """Parse the content and return a list of statements."""
        self.errors = []
        self.statements = []
        lines = content.split('\n')
        
        try:
            self._parse_lines(lines)
            if self.strict_mode and self.errors:
                raise ValueError("\n".join(str(error) for error in self.errors))
        except Exception as e:
            if self.strict_mode:
                raise
            self.errors.append(ParserError(
                self.current_line,
                str(e),
                "Error during parsing"
            ))
            
        return self.statements

    def _parse_lines(self, lines: List[str]):
        """Parse lines sequentially."""
        for i, line in enumerate(lines):
            self.current_line = i + 1
            stripped_line = line.lstrip()
            
            if not stripped_line or stripped_line.isspace():
                continue
                
            line_type = self._determine_line_type(stripped_line)
            
            try:
                self._process_line(stripped_line, line_type)
            except Exception as e:
                self.errors.append(ParserError(
                    self.current_line,
                    str(e),
                    line
                ))
                if self.strict_mode:
                    raise

    def _determine_line_type(self, line: str) -> LineType:
        """Determine the type of line according to format rules."""
        if line.startswith('#'):
            return LineType.COMMENT
        elif line.startswith('.'):
            return LineType.TEXT_BLOCK
        elif line.startswith('-'):
            return LineType.LIST_ITEM
        elif ':' in line:
            return LineType.KEY_VALUE
        elif line.startswith('/'):
            return LineType.BLOCK_START
        elif line.endswith('/'):
            return LineType.BLOCK_END
        elif line.strip().isalnum() or ' ' in line.strip():
            return LineType.STATEMENT
        else:
            return LineType.BLOCK_CONTENT

    def _process_line(self, line: str, line_type: LineType):
        """Process a line based on its type."""
        if line_type == LineType.COMMENT:
            return
            
        elif line_type == LineType.BLOCK_START:
            self._process_block_start(line)
            
        elif line_type == LineType.BLOCK_END:
            self._process_block_end(line)
            
        elif self.current_block is not None:
            # We're inside a block, handle statement and its parameters
            if line_type == LineType.STATEMENT:
                self._process_statement_in_block(line)
            elif self.current_statement:  # Process parameters for the current block statement
                if line_type == LineType.KEY_VALUE:
                    self._process_key_value(line)
                elif line_type == LineType.TEXT_BLOCK:
                    self._process_text_block(line)
                elif line_type == LineType.LIST_ITEM:
                    self._process_list_item(line)
        else:
            # Outside block processing
            if line_type == LineType.STATEMENT:
                self._process_statement(line)
            elif line_type == LineType.KEY_VALUE:
                self._process_key_value(line)
            elif line_type == LineType.TEXT_BLOCK:
                self._process_text_block(line)
            elif line_type == LineType.LIST_ITEM:
                self._process_list_item(line)

    def _process_statement(self, line: str):
        """Process a statement line."""
        if len(line) > 100:  # Example character limit
            raise ValueError("Statement exceeds maximum length")
            
        self.current_statement = Statement(line.strip(), self.current_line)
        self.statements.append(self.current_statement)
        self.current_key = None

    def _process_statement_in_block(self, line: str):
        """Process a statement within a block."""
        if len(line) > 100:  # Example character limit
            raise ValueError("Statement exceeds maximum length")
            
        statement = Statement(line.strip(), self.current_line)
        if self.current_block and self.parent_statement:
            self.parent_statement.blocks[self.current_block].append(statement)
        self.current_statement = statement
        self.current_key = None

    def _process_key_value(self, line: str):
        """Process a key/value line."""
        if not self.current_statement:
            raise ValueError("Key/value pair outside of statement context")
            
        key, value = [part.strip() for part in line.split(':', 1)]
        
        if not key.isalnum():
            raise ValueError("Invalid key format")
            
        if key in self.current_statement.parameters:
            raise ValueError(f"Duplicate key: {key}")
            
        self.current_key = key
        
        if value:  # Inline value
            self.current_statement.parameters[key] = value
            self.current_key = None
        else:  # Expecting text block or list to follow
            self.current_statement.parameters[key] = []

    def _process_text_block(self, line: str):
        """Process a text block line."""
        if not self.current_key:
            raise ValueError("Text block without associated key")
            
        if isinstance(self.current_statement.parameters[self.current_key], list):
            # First text block line
            self.current_statement.parameters[self.current_key] = line[1:]
        else:
            # Append to existing text block
            self.current_statement.parameters[self.current_key] += "\n" + line[1:]

    def _process_list_item(self, line: str):
        """Process a list item line."""
        if not self.current_key:
            raise ValueError("List item without associated key")
            
        level = len(line) - len(line.lstrip('-'))
        if level > 5:
            raise ValueError("List nesting too deep")
            
        content = line.lstrip('- ').strip()
        
        if not isinstance(self.current_statement.parameters[self.current_key], list):
            raise ValueError("Mixed content types not allowed")
            
        current_list = self.current_statement.parameters[self.current_key]
        
        # Handle nesting
        for _ in range(level - 1):
            if not current_list or not isinstance(current_list[-1], list):
                current_list.append([])
            current_list = current_list[-1]
            
        current_list.append(content)

    def _process_block_start(self, line: str):
        """Process a block start line."""
        if not self.current_statement:
            raise ValueError("Block start outside of statement context")
            
        block_name = line[1:].strip()
        if not block_name.isalnum():
            raise ValueError("Invalid block name")
            
        if block_name in self.current_statement.blocks:
            raise ValueError(f"Duplicate block name: {block_name}")
            
        self.current_block = block_name
        self.current_statement.blocks[block_name] = []
        self.parent_statement = self.current_statement
        self.current_key = None

    def _process_block_end(self, line: str):
        """Process a block end line."""
        block_name = line[:-1].strip()
        if block_name != self.current_block:
            raise ValueError(f"Mismatched block end: expected {self.current_block}, got {block_name}")
            
        self.current_block = None
        self.current_key = None
        self.current_statement = self.parent_statement
        self.parent_statement = None

def parse_clear_statement_format(content: str, strict_mode: bool = True) -> List[Statement]:
    """
    Parse content in Clear Statement Format and return a list of statements.
    
    Args:
        content (str): The content to parse
        strict_mode (bool): Whether to use strict mode parsing
        
    Returns:
        List[Statement]: The parsed statements
        
    Raises:
        ValueError: If parsing fails in strict mode
    """
    parser = ClearStatementParser(strict_mode=strict_mode)
    return parser.parse(content)

if __name__ == "__main__":
    # Example content demonstrating various features
    example_content = """# This is a comment
# This demonstrates various features of the Clear Statement Format

Create Project
    name: MyWebApp
    description:
    .A web application that provides user authentication
    .and dashboard functionality for monitoring system metrics
    
    dependencies:
    - Python 3.9+
    - PostgreSQL
    -- psycopg2
    -- sqlalchemy
    - Redis
    
    /Configuration
        Set Environment
            variables:
            - DATABASE_URL
            - REDIS_HOST
            - SECRET_KEY
        
        Setup Database
            commands:
            .createdb mywebapp
            .python manage.py migrate
    Configuration/

Deploy Application
    target: production
    steps:
    - Build Docker image
    - Run tests
    - Push to registry
    - Update Kubernetes deployment

    /Notifications
        Send Email
            to: devops@company.com
            subject: Deployment Status
            body:
            .Deployment to production completed
            .
            .Status: {status}
            .Time: {timestamp}
    Notifications/
"""

    # Parse in strict mode
    statements = parse_clear_statement_format(example_content)
    
    # Display parsed results
    print("Parsed Statements:")
    print("=================")
    
    for i, statement in enumerate(statements, 1):
        print(f"\n{i}. {repr(statement)}")