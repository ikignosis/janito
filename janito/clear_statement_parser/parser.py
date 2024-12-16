from dataclasses import dataclass
from typing import Dict, List, Union, Optional, Tuple
from enum import Enum
import re

class LineType(Enum):
    EMPTY = "empty"
    COMMENT = "comment"
    LIST_ITEM = "list_item"
    STATEMENT = "statement"
    LITERAL_BLOCK = "literal_block"
    KEY_VALUE = "key_value"
    BLOCK_BEGIN = "block_begin"
    BLOCK_END = "block_end"

@dataclass
class ParseError(Exception):
    line_number: int
    statement_context: str
    message: str

    def __str__(self):
        return f"Line {self.line_number}: {self.message} (in statement: {self.statement_context})"

class Statement:
    def __init__(self, name: str):
        self.name = name
        self.parameters: Dict[str, Union[str, List, Dict]] = {}
        self.blocks: List[Tuple[str, List[Statement]]] = []
        
    def to_dict(self) -> Dict:
        """Convert the statement to a dictionary representation"""
        result = {
            'name': self.name,
            'parameters': self.parameters.copy(),
            'blocks': []
        }
        
        # Convert nested statements in blocks to dicts
        for block_name, block_statements in self.blocks:
            block_dicts = [stmt.to_dict() for stmt in block_statements]
            result['blocks'].append({
                'name': block_name,
                'statements': block_dicts
            })
            
        return result
        
    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        indent = 0
        return self._repr_recursive(indent)
    
    def _repr_recursive(self, indent: int, max_line_length: int = 80) -> str:
        lines = []
        prefix = "  " * indent
        
        # Add statement name
        lines.append(f"{prefix}{self.name}")
        
        # Add parameters with proper indentation
        for key, value in self.parameters.items():
            if isinstance(value, str) and '\n' in value:
                # Handle multiline string values (literal blocks)
                lines.append(f"{prefix}  {key}:")
                for line in value.split('\n'):
                    lines.append(f"{prefix}    .{line}")
            elif isinstance(value, list):
                # Handle nested lists with proper indentation
                lines.append(f"{prefix}  {key}:")
                lines.extend(self._format_list(value, indent + 2))
            else:
                # Handle simple key-value pairs
                value_str = repr(value) if isinstance(value, str) else str(value)
                if len(f"{prefix}  {key}: {value_str}") <= max_line_length:
                    lines.append(f"{prefix}  {key}: {value_str}")
                else:
                    lines.append(f"{prefix}  {key}:")
                    lines.append(f"{prefix}    {value_str}")
        
        # Add blocks with proper indentation and block markers
        for block_name, block_statements in self.blocks:
            lines.append(f"{prefix}  /{block_name}")
            for statement in block_statements:
                lines.append(statement._repr_recursive(indent + 2))
            lines.append(f"{prefix}  {block_name}/")
        
        return "\n".join(lines)
    
    def _format_list(self, lst: List, indent: int) -> List[str]:
        lines = []
        prefix = "  " * indent
        
        def format_nested(items, depth=0):
            for item in items:
                if isinstance(item, list):
                    format_nested(item, depth + 1)
                else:
                    lines.append(f"{prefix}{'-' * (depth + 1)} {item}")
        
        format_nested(lst)
        return lines

class BlockContext:
    def __init__(self, name: str, line_number: int, parent: Optional['BlockContext'] = None):
        self.name = name
        self.line_number = line_number
        self.parent = parent
        self.statements: List[Statement] = []
        self.current_statement: Optional[Statement] = None
        self.parameter_type: Optional[LineType] = None
        self._block_counters: Dict[str, int] = {}  # Track block counters by base name

    def validate_block_name(self, name: str, line_number: int) -> str:
        """Generate internal tracking name for blocks"""
        if name not in self._block_counters:
            self._block_counters[name] = 0
            
        # Increment counter and generate internal name if needed
        self._block_counters[name] += 1
        if self._block_counters[name] > 1:
            return f"{name}#{self._block_counters[name]}"
            
        return name

    def get_base_name(self) -> str:
        """Get the base name without any internal counter"""
        return self.name.split('#')[0]
        
    def validate_block_end(self, name: str, line_number: int) -> bool:
        """Validate block end name matches current context"""
        return name == self.get_base_name()

    def new_statement(self):
        """Reset statement-specific tracking when starting a new statement"""
        self._block_counters.clear()
        self.current_statement = None
        self.parameter_type = None

class StatementParser:
    def __init__(self):
        self.max_list_depth = 5
        self.max_block_depth = 10
        self.errors: List[ParseError] = []
        self.debug = False
        
    def parse(self, content: str, debug: bool = False) -> List[Statement]:
        self.debug = debug
        self.errors = []
        lines = content.splitlines()
        
        if self.debug:
            print("\nStarting parse with debug mode enabled")
            
        context = BlockContext("root", -1)
        self._parse_context(lines, 0, len(lines), context)
        return context.statements

    def _parse_context(self, lines: List[str], start: int, end: int, context: BlockContext) -> int:
        """Parse statements within the current block context"""
        line_number = start
        
        while line_number < end:
            line = lines[line_number].strip()
            line_type = self._determine_line_type(line)
            
            if self.debug:
                self._print_debug_info(line_number, line, line_type, context)
            
            try:
                # Handle each line type according to spec
                if line_type in (LineType.EMPTY, LineType.COMMENT):
                    line_number += 1
                    continue
                    
                elif line_type == LineType.STATEMENT:
                    context.new_statement()  # Reset statement context
                    context.current_statement = Statement(line)
                    context.statements.append(context.current_statement)
                    context.parameter_type = None
                    line_number += 1
                    
                elif line_type == LineType.BLOCK_BEGIN:
                    if not context.current_statement:
                        raise ParseError(line_number, "", "Block begin found outside statement")
                        
                    base_name = self._validate_block_name(line[1:].strip(), line_number)
                    tracked_name = context.validate_block_name(base_name, line_number)
                    new_context = BlockContext(tracked_name, line_number, context)
                    
                    if self.debug:
                        print(f"  Opening block '{tracked_name}' at line {line_number + 1}")
                    
                    # Parse nested block
                    line_number = self._parse_context(lines, line_number + 1, end, new_context)
                    context.current_statement.blocks.append((tracked_name, new_context.statements))
                    continue
                    
                elif line_type == LineType.BLOCK_END:
                    base_name = line[:-1].strip()  # Remove trailing slash
                    
                    if not context.parent:
                        raise ParseError(line_number, "", 
                            f"Unexpected block end '{base_name}', no blocks are currently open")
                    
                    if not context.validate_block_end(base_name, line_number):
                        raise ParseError(line_number, "",
                            f"Mismatched block end '{base_name}', expected '{context.get_base_name()}' (opened at line {context.line_number + 1})")
                    
                    if self.debug:
                        print(f"  Closing block '{context.name}' opened at line {context.line_number + 1}")
                    
                    return line_number + 1
                
                else:
                    # Handle parameter types (key/value, list, literal block)
                    line_number = self._handle_parameter(line_number, lines, line_type, context)
                    
            except ParseError as e:
                self.errors.append(e)
                line_number += 1
                
        # Check for unclosed blocks at end of input
        if context.parent is not None:
            raise ParseError(end, "", 
                f"Reached end of input without closing block '{context.name}' (opened at line {context.line_number + 1})")
        
        return line_number

    def _handle_parameter(self, line_number: int, lines: List, line_type: LineType, context: BlockContext) -> int:
        """Handle parameter parsing according to spec rules"""
        if not context.current_statement:
            raise ParseError(line_number, "", f"{line_type.value} found outside statement")
            
        if context.parameter_type and context.parameter_type != line_type:
            raise ParseError(line_number, context.current_statement.name, 
                "Cannot mix different parameter types")
            
        context.parameter_type = line_type
        
        if line_type == LineType.KEY_VALUE:
            return self._parse_key_value(line_number, lines, context)
        elif line_type == LineType.LIST_ITEM:
            return self._parse_list_items(line_number, lines, context)
        elif line_type == LineType.LITERAL_BLOCK:
            return self._parse_literal_block(line_number, lines, context)
        
        return line_number + 1

    def _determine_line_type(self, line: str) -> LineType:
        """Determine the type of a line based on its content"""
        if not line:
            return LineType.EMPTY
        if line.startswith("#"):
            return LineType.COMMENT
        if line.startswith("-"):
            return LineType.LIST_ITEM
        if line.startswith("."):
            return LineType.LITERAL_BLOCK
        if ":" in line:
            return LineType.KEY_VALUE
        if line.startswith("/"):
            return LineType.BLOCK_BEGIN
        if line.endswith("/"):
            return LineType.BLOCK_END
        if not all(c.isalnum() or c.isspace() for c in line):
            raise ParseError(0, line, "Statements must contain only alphanumeric characters and spaces")
        return LineType.STATEMENT
    
    def _validate_block_name(self, name: str, line_number: int) -> str:
        """Validate block name contains only alphanumeric characters"""
        if '#' in name:
            raise ParseError(line_number, name, "Block names cannot contain '#' characters")
        if not name.isalnum():
            raise ParseError(line_number, name, "Block names must contain only alphanumeric characters")
        return name
    
    def _parse_key_value(self, line_number: int, lines: List[str], context: BlockContext) -> int:
        """Parse a key-value line, stripping whitespace after the colon"""
        line = lines[line_number].strip()
        key, value = line.split(":", 1)
        key, value = key.strip(), value.strip()
        
        if key in context.current_statement.parameters:
            raise ParseError(line_number, context.current_statement.name, f"Duplicate key: {key}")
            
        if not value:  # Empty value means we expect a literal block or list to follow
            line_number, value = self._parse_complex_value(lines, line_number + 1)
        
        context.current_statement.parameters[key] = value
        return line_number + 1
    
    def _parse_complex_value(self, lines: List[str], start_line: int) -> tuple[int, Union[str, List]]:
        if start_line >= len(lines):
            raise ParseError(start_line - 1, "", "Expected literal block or list after empty value")
            
        next_line = lines[start_line].strip()
        if next_line.startswith("."):
            return self._parse_literal_block_value(lines, start_line)
        elif next_line.startswith("-"):
            return self._parse_list_value(lines, start_line)
        else:
            raise ParseError(start_line, "", "Expected literal block or list after empty value")
    
    def _parse_literal_block_value(self, lines: List[str], start_line: int) -> tuple[int, str]:
        """Parse a literal block value, preserving content after the leading dot"""
        literal_lines = []
        current_line = start_line
        
        while current_line < len(lines):
            line = lines[current_line].strip()
            if not line or line.startswith("#"):
                current_line += 1
                continue
                
            if not line.startswith("."):
                break
                
            content = line[1:]  # Strip only the leading dot
            literal_lines.append(content)
            current_line += 1
            
        if not literal_lines:
            raise ParseError(start_line, "", "Empty literal block")
            
        return current_line - 1, "\n".join(literal_lines)

    def _parse_list_value(self, lines: List[str], start_line: int) -> tuple[int, List]:
        result = []
        current_depth = 0
        current_line = start_line
        
        while current_line < len(lines):
            line = lines[current_line].strip()
            if not line or line.startswith("#"):
                current_line += 1
                continue
                
            if not line.startswith("-"):
                break
                
            depth = len(re.match(r'-+', line).group())
            if depth > self.max_list_depth:
                raise ParseError(current_line, "", f"Maximum list depth of {self.max_list_depth} exceeded")
                
            if depth > current_depth + 1:
                raise ParseError(current_line, "", f"Invalid list nesting: skipped level {current_depth + 1}")
                
            content = line[depth:].strip()
            if not content:
                raise ParseError(current_line, "", "Empty list item")
                
            current_node = result
            for _ in range(depth - 1):
                if not current_node or not isinstance(current_node[-1], list):
                    current_node.append([])
                current_node = current_node[-1]
                
            current_node.append(content)
            current_depth = depth
            current_line += 1
            
        if not result:
            raise ParseError(start_line, "", "Empty list")
            
        return current_line - 1, result

    def _parse_list_items(self, line_number: int, lines: List[str], context: BlockContext) -> int:
        _, items = self._parse_list_value(lines, line_number)
        context.current_statement.parameters["items"] = items
        return line_number + 1
    
    def _parse_literal_block(self, line_number: int, lines: List[str], context: BlockContext) -> int:
        _, text = self._parse_literal_block_value(lines, line_number)
        context.current_statement.parameters["text"] = text
        return line_number + 1

    def _print_debug_info(self, line_number: int, line: str, line_type: LineType, context: BlockContext) -> None:
        """Print debug information about current parsing state"""
        print(f"\nLine {line_number + 1}: Type={line_type.value}, Content='{line}'")
        
        # Print block context chain
        current = context
        if current.name != "root":
            chain = []
            while current and current.name != "root":
                chain.append(f"'{current.name}' (line {current.line_number + 1})")
                current = current.parent
            print("  Block context:", " -> ".join(reversed(chain)))

    def print_statements(self, statements: List[Statement]) -> None:
        """Print statements in a hierarchical structure format"""
        for statement in statements:
            print(f"\nStatement: {statement.name}")
            self._print_statement_structure(statement, indent=2)

    def _print_statement_structure(self, statement: Statement, indent: int = 0) -> None:
        """Recursively print statement structure"""
        prefix = " " * indent
        
        # Print parameters
        if statement.parameters:
            print(f"{prefix}Parameters:")
            for key, value in statement.parameters.items():
                if isinstance(value, str) and '\n' in value:
                    print(f"{prefix}  {key}: <multiline-content>")
                elif isinstance(value, list):
                    print(f"{prefix}  {key}: <list-content>")
                else:
                    print(f"{prefix}  {key}: {value}")
        
        # Print blocks
        if statement.blocks:
            print(f"{prefix}Blocks:")
            for block_name, block_statements in statement.blocks:
                print(f"{prefix}  {block_name}:")
                for nested_stmt in block_statements:
                    self._print_statement_structure(nested_stmt, indent + 4)

if __name__ == "__main__":
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description='Parse a clear statement file')
    parser.add_argument('file_path', help='Path to the input file')
    parser.add_argument('--debug', '-d', action='store_true', help='Enable debug output')
    
    args = parser.parse_args()
    
    try:
        with open(args.file_path, 'r') as f:
            content = f.read()
            
        statement_parser = StatementParser()
        statements = statement_parser.parse(content, debug=args.debug)
        
        if statement_parser.errors:
            print("\nParsing errors:")
            for error in statement_parser.errors:
                print(error)
            sys.exit(1)
        else:
            print(f"\nSuccessfully parsed statements from {args.file_path}:")
            print("=" * 50)
            statement_parser.print_statements(statements)
            
    except FileNotFoundError:
        print(f"Error: File '{args.file_path}' not found")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)