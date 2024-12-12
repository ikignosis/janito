from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum

class LineType(Enum):
    COMMENT = "COMMENT"
    STATEMENT = "STATEMENT"
    TEXT_BLOCK = "TEXT_BLOCK"
    KEY_VALUE = "KEY_VALUE"
    SECTION_START = "SECTION_START"
    SECTION_END = "SECTION_END"
    EMPTY = "EMPTY"

@dataclass
class Statement:
    name: str
    text: str = ""
    key_values: Dict[str, str] = field(default_factory=dict)
    sections: Dict[str, List['Statement']] = field(default_factory=dict)
    parent: Optional['Statement'] = None
    line_number: int = 0

class ParsingError(Exception):
    def __init__(self, message: str, line_number: int, context: Optional[List[str]] = None):
        self.message = message
        self.line_number = line_number
        self.context = context or []
        super().__init__(f"Line {line_number}: {message} (Context: {' > '.join(self.context)})")

class SSFParser:
    def __init__(self):
        self.current_line = 0
        self.section_stack: List[str] = []
        
    def identify_line_type(self, line: str) -> LineType:
        """Identify the type of a line based on the format rules."""
        stripped_line = line.lstrip()
        
        if not stripped_line:
            return LineType.EMPTY
        if stripped_line.startswith('#'):
            return LineType.COMMENT
        if stripped_line.startswith('.'):
            return LineType.TEXT_BLOCK
        if ':' in stripped_line:
            return LineType.KEY_VALUE
        if stripped_line.startswith('/'):
            return LineType.SECTION_START
        if stripped_line.endswith('/'):
            return LineType.SECTION_END
        return LineType.STATEMENT

    def get_indentation(self, line: str) -> int:
        """Get the indentation level of a line."""
        return len(line) - len(line.lstrip())

    def parse(self, content: str) -> List[Statement]:
        """Parse the SSF content and return a list of statements."""
        lines = content.splitlines()
        statements: List[Statement] = []
        current_statement: Optional[Statement] = None
        text_block_lines: List[str] = []
        
        self.current_line = 0
        self.section_stack = []
        
        while self.current_line < len(lines):
            original_line = lines[self.current_line]
            line = original_line.rstrip()
            line_type = self.identify_line_type(line)
            
            try:
                if line_type == LineType.EMPTY or line_type == LineType.COMMENT:
                    self.current_line += 1
                    continue
                
                elif line_type == LineType.STATEMENT:
                    if text_block_lines:
                        if current_statement:
                            current_statement.text = '\n'.join(text_block_lines)
                        text_block_lines = []
                    
                    current_statement = Statement(
                        name=line.strip(),
                        line_number=self.current_line + 1
                    )
                    
                    if self.section_stack:
                        parent_statement = statements[-1]
                        for section in self.section_stack[:-1]:
                            parent_statement = parent_statement.sections[section][-1]
                        
                        current_statement.parent = parent_statement
                        section_name = self.section_stack[-1]
                        if section_name not in parent_statement.sections:
                            parent_statement.sections[section_name] = []
                        parent_statement.sections[section_name].append(current_statement)
                    else:
                        statements.append(current_statement)
                
                elif line_type == LineType.TEXT_BLOCK:
                    if line.lstrip().startswith('.'):
                        # Find the position of the dot and keep everything after it
                        dot_pos = line.find('.')
                        text_content = line[dot_pos + 1:]
                        text_block_lines.append(text_content)
                    else:
                        text_block_lines.append(line)
                
                elif line_type == LineType.KEY_VALUE:
                    if text_block_lines:
                        if current_statement:
                            current_statement.text = '\n'.join(text_block_lines)
                        text_block_lines = []
                    
                    key, value = [x.strip() for x in line.split(':', 1)]
                    if current_statement:
                        if key in current_statement.key_values:
                            raise ParsingError(f"Duplicate key '{key}' found", self.current_line + 1)
                        current_statement.key_values[key] = value
                
                elif line_type == LineType.SECTION_START:
                    section_name = line.lstrip().lstrip('/').strip()
                    if not section_name.isalnum():
                        raise ParsingError("Section name must be alphanumeric", self.current_line + 1)
                    if current_statement and section_name in current_statement.sections:
                        raise ParsingError(f"Duplicate section '{section_name}' found", self.current_line + 1)
                    self.section_stack.append(section_name)
                
                elif line_type == LineType.SECTION_END:
                    section_name = line.rstrip().rstrip('/').strip()
                    if not self.section_stack:
                        raise ParsingError("Unexpected section end", self.current_line + 1)
                    if self.section_stack[-1] != section_name:
                        raise ParsingError(
                            f"Section end mismatch. Expected '{self.section_stack[-1]}', got '{section_name}'",
                            self.current_line + 1
                        )
                    if current_statement and section_name in current_statement.sections:
                        if not current_statement.sections[section_name]:
                            raise ParsingError(f"Empty section '{section_name}' is not allowed", self.current_line + 1)
                    self.section_stack.pop()
            
            except Exception as e:
                if not isinstance(e, ParsingError):
                    e = ParsingError(str(e), self.current_line + 1, self.section_stack)
                raise e
            
            self.current_line += 1
        
        if self.section_stack:
            raise ParsingError(
                f"Unclosed sections: {', '.join(self.section_stack)}",
                self.current_line,
                self.section_stack
            )
        
        return statements

class SSFExecutor:
    def __init__(self):
        self.handlers: Dict[str, Any] = {}
        self.section_handlers: Dict[str, Dict[str, Any]] = {}
        
    def register_handler(self, statement_name: str, handler, section: Optional[str] = None):
        """
        Register a handler function for a specific statement type.
        If section is provided, registers the handler for that specific section context.
        """
        if section:
            if section not in self.section_handlers:
                self.section_handlers[section] = {}
            self.section_handlers[section][statement_name] = handler
        else:
            self.handlers[statement_name] = handler
    
    def execute(self, statements: List[Statement]) -> None:
        """Execute the parsed statements in order."""
        try:
            for statement in statements:
                self._execute_statement(statement)
        except Exception as e:
            context = []
            current = statement
            while current:
                context.insert(0, current.name)
                current = current.parent
            raise RuntimeError(f"Error executing statement '{statement.name}' at line {statement.line_number}: {str(e)}\nContext: {' > '.join(context)}")
    
    def _execute_statement(self, statement: Statement) -> Any:
        """Execute a single statement and its sections. Returns the handler's result if any."""
        # Determine the correct handler based on context
        handler = None
        if statement.parent:
            # Check for section-specific handlers
            parent_sections = statement.parent.sections.keys()
            for section_name in parent_sections:
                if section_name in self.section_handlers and statement.name in self.section_handlers[section_name]:
                    handler = self.section_handlers[section_name][statement.name]
                    break
        
        # Fall back to global handlers if no section-specific handler found
        if handler is None:
            if statement.name not in self.handlers:
                raise ValueError(f"No handler registered for statement type: {statement.name}")
            handler = self.handlers[statement.name]
        
        # Execute the handler and store result
        result = handler(statement)
        
        # Execute any nested sections
        for section_statements in statement.sections.values():
            for section_statement in section_statements:
                self._execute_statement(section_statement)
        
        return result

class FileState:
    def __init__(self):
        self.files = {}
        self.current_selections = {}
    
    def create_file(self, filename: str, content: str):
        self.files[filename] = content
        print(f"Created file '{filename}' with content:\n{content}")
    
    def select_text(self, filename: str, text: str) -> bool:
        if filename not in self.files:
            raise ValueError(f"File '{filename}' does not exist")
        if text not in self.files[filename]:
            raise ValueError(f"Text '{text}' not found in file '{filename}'")
        self.current_selections[filename] = text
        print(f"Selected text in '{filename}': {text}")
        return True
    
    def replace_text(self, filename: str, new_text: str):
        if filename not in self.files or filename not in self.current_selections:
            raise ValueError(f"No active selection in file '{filename}'")
        old_text = self.current_selections[filename]
        self.files[filename] = self.files[filename].replace(old_text, new_text)
        print(f"Replaced text in '{filename}':\nOld: {old_text}\nNew: {new_text}")
    
    def delete_text(self, filename: str):
        if filename not in self.files or filename not in self.current_selections:
            raise ValueError(f"No active selection in file '{filename}'")
        old_text = self.current_selections[filename]
        self.files[filename] = self.files[filename].replace(old_text, '')
        print(f"Deleted text in '{filename}': {old_text}")

def main():
    # Initialize parser, executor and file state
    parser = SSFParser()
    executor = SSFExecutor()
    file_state = FileState()

    # Handler implementations
    def handle_create_file(statement: Statement):
        filename = statement.key_values['name']
        content = statement.text
        file_state.create_file(filename, content)

    def handle_modify_file(statement: Statement):
        filename = statement.key_values['file']
        print(f"Starting modifications for file: {filename}")

    def handle_select_text(statement: Statement):
        parent = statement.parent
        if not parent or 'file' not in parent.key_values:
            raise ValueError("Select Text must be within a Modify File statement")
        filename = parent.key_values['file']
        return file_state.select_text(filename, statement.text)

    def handle_replace_with(statement: Statement):
        parent = statement.parent
        if not parent or 'file' not in parent.key_values:
            raise ValueError("Replace With must be within a Modify File statement")
        filename = parent.key_values['file']
        file_state.replace_text(filename, statement.text)

    def handle_delete(statement: Statement):
        parent = statement.parent
        if not parent or 'file' not in parent.key_values:
            raise ValueError("Delete must be within a Modify File statement")
        filename = parent.key_values['file']
        file_state.delete_text(filename)

    # Register the handlers
    executor.register_handler('Create File', handle_create_file)
    executor.register_handler('Modify File', handle_modify_file)
    executor.register_handler('Select Text', handle_select_text, 'Modifications')
    executor.register_handler('Replace With', handle_replace_with, 'Modifications')
    executor.register_handler('Delete', handle_delete, 'Modifications')

    # Example SSF content demonstrating indentation preservation
    ssf_content = """# Create initial file with indented content
Create File
name: example.py
.def hello():
.    print("Hello, World!")
.    if True:
.        print("Deeply indented!")
.        for i in range(3):
.            print(f"Count: {i}")
.
.hello()

# Modify the file
Modify File
    file: example.py
/Modifications
Select Text
.def hello():
.    print("Hello, World!")
.    if True:
.        print("Deeply indented!")
Replace With
.def hello():
.    print("Hello, Universe!")
.    if True:
.        print("Still indented!")
Select Text
.        for i in range(3):
.            print(f"Count: {i}")
Delete
Modifications/"""

    try:
        # Parse and execute
        print("Parsing and executing SSF content...")
        statements = parser.parse(ssf_content)
        executor.execute(statements)

        # Show final file state
        print("\nFinal file contents:")
        for filename, content in file_state.files.items():
            print(f"\n{filename}:\n{content}")

    except ParsingError as e:
        print(f"Parsing error: {e}")
    except RuntimeError as e:
        print(f"Execution error: {e}")

if __name__ == "__main__":
    main()