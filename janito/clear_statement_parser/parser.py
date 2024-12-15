from dataclasses import dataclass
from typing import Dict, List, Union, Optional
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
        self.blocks: Dict[str, List[Statement]] = {}
        
    def __str__(self):
        parts = [f"Statement(name={self.name}"]
        
        if self.parameters:
            params_str = ", ".join(f"{k}: {repr(v)}" for k, v in self.parameters.items())
            parts.append(f"params={{{params_str}}}")
            
        if self.blocks:
            blocks_str = ", ".join(
                f"{k}: {len(v)} statement(s)" for k, v in self.blocks.items()
            )
            parts.append(f"blocks={{{blocks_str}}}")
        else:
            parts.append("blocks={}")
            
        return ", ".join(parts) + ")"

    def __repr__(self):
        return self.__str__()

class StatementParser:
    def __init__(self):
        self.max_list_depth = 5
        self.max_block_depth = 10
        self.errors: List[ParseError] = []
        
    def parse(self, content: str) -> List[Statement]:
        self.errors = []
        lines = content.splitlines()
        return self._parse_statements(lines, 0, len(lines))[0]
    
    def _parse_statements(self, lines: List[str], start: int, end: int, depth: int = 0) -> tuple[List[Statement], int]:
        if depth > self.max_block_depth:
            raise ParseError(start, "", f"Maximum block nesting depth of {self.max_block_depth} exceeded")
            
        statements = []
        current_statement = None
        parameter_type = None
        line_number = start
        
        while line_number < end:
            line = lines[line_number].strip()
            line_type = self._determine_line_type(line)
            
            try:
                if line_type == LineType.EMPTY or line_type == LineType.COMMENT:
                    line_number += 1
                    continue
                    
                elif line_type == LineType.STATEMENT:
                    if parameter_type is not None:
                        parameter_type = None
                    current_statement = Statement(line)
                    statements.append(current_statement)
                    line_number += 1
                    
                elif line_type == LineType.KEY_VALUE:
                    if not current_statement:
                        raise ParseError(line_number, "", "Key/value pair found outside statement")
                    if parameter_type and parameter_type != LineType.KEY_VALUE:
                        raise ParseError(line_number, current_statement.name, "Cannot mix different parameter types")
                    parameter_type = LineType.KEY_VALUE
                    key, value = self._parse_key_value(line)
                    if key in current_statement.parameters:
                        raise ParseError(line_number, current_statement.name, f"Duplicate key: {key}")
                        
                    if not value:  # Empty value means we expect a literal block or list to follow
                        line_number, value = self._parse_complex_value(lines, line_number + 1)
                    
                    current_statement.parameters[key] = value
                    line_number += 1
                    
                elif line_type == LineType.LIST_ITEM:
                    if not current_statement:
                        raise ParseError(line_number, "", "List item found outside statement")
                    if parameter_type and parameter_type != LineType.LIST_ITEM:
                        raise ParseError(line_number, current_statement.name, "Cannot mix different parameter types")
                    parameter_type = LineType.LIST_ITEM
                    line_number = self._parse_list_items(lines, line_number, current_statement)
                    line_number += 1
                    
                elif line_type == LineType.LITERAL_BLOCK:
                    if not current_statement:
                        raise ParseError(line_number, "", "Literal block found outside statement")
                    if parameter_type and parameter_type != LineType.LITERAL_BLOCK:
                        raise ParseError(line_number, current_statement.name, "Cannot mix different parameter types")
                    parameter_type = LineType.LITERAL_BLOCK
                    line_number = self._parse_literal_block(lines, line_number, current_statement)
                    line_number += 1
                    
                elif line_type == LineType.BLOCK_BEGIN:
                    if not current_statement:
                        raise ParseError(line_number, "", "Block begin found outside statement")
                    
                    block_name = self._validate_block_name(line[1:].strip(), line_number)
                    if block_name in current_statement.blocks:
                        raise ParseError(line_number, current_statement.name, f"Duplicate block name: {block_name}")
                    
                    nested_statements, new_line_number = self._parse_statements(lines, line_number + 1, end, depth + 1)
                    current_statement.blocks[block_name] = nested_statements
                    line_number = new_line_number
                    
                elif line_type == LineType.BLOCK_END:
                    block_name = self._validate_block_name(line[:-1].strip(), line_number)
                    return statements, line_number + 1
                
                else:
                    line_number += 1
                    
            except ParseError as e:
                self.errors.append(e)
                line_number += 1
                
        return statements, line_number

    def print_statements(self, statements: List[Statement], indent: int = 0):
        """Pretty print the statements with proper indentation for blocks"""
        for statement in statements:
            print("  " * indent + str(statement))
            for block_name, block_statements in statement.blocks.items():
                print("  " * (indent + 1) + f"{block_name}:")
                self.print_statements(block_statements, indent + 2)
    
    def _determine_line_type(self, line: str) -> LineType:
        """Determine the type of a line based on its content"""
        if not line:
            return LineType.EMPTY
        if line.startswith("#"):
            return LineType.COMMENT
        if line.startswith("-"):
            return LineType.LIST_ITEM
        if line.startswith("."):
            return LineType.LITERAL_BLOCK  # Changed from TEXT_BLOCK
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
        if not name.isalnum():
            raise ParseError(line_number, name, "Block names must contain only alphanumeric characters")
        return name
    
    def _parse_key_value(self, line: str) -> tuple[str, str]:
        """Parse a key-value line, stripping whitespace after the colon"""
        key, value = line.split(":", 1)
        return key.strip(), value.strip()
    
    def _parse_complex_value(self, lines: List[str], start_line: int) -> tuple[int, Union[str, List]]:
        if start_line >= len(lines):
            raise ParseError(start_line - 1, "", "Expected literal block or list after empty value")
            
        next_line = lines[start_line].strip()
        if next_line.startswith("."):
            return self._parse_literal_block_value(lines, start_line)  # Changed method name
        elif next_line.startswith("-"):
            return self._parse_list_value(lines, start_line)
        else:
            raise ParseError(start_line, "", "Expected literal block or list after empty value")
    
    def _parse_literal_block_value(self, lines: List[str], start_line: int) -> tuple[int, str]:  # Changed method name
        """Parse a literal block value, preserving content after the leading dot"""
        literal_lines = []  # Changed variable name
        current_line = start_line
        
        while current_line < len(lines):
            line = lines[current_line].strip()
            if not line or line.startswith("#"):
                current_line += 1
                continue
                
            if not line.startswith("."):
                break
                
            content = line[1:]  # Strip only the leading dot
            literal_lines.append(content)  # Changed variable name
            current_line += 1
            
        if not literal_lines:  # Changed variable name
            raise ParseError(start_line, "", "Empty literal block")
            
        return current_line - 1, "\n".join(literal_lines)  # Changed variable name

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

    def _parse_list_items(self, lines: List[str], start_line: int, statement: Statement) -> int:
        _, items = self._parse_list_value(lines, start_line)
        statement.parameters["items"] = items
        return start_line
    
    def _parse_literal_block(self, lines: List[str], start_line: int, statement: Statement) -> int:  # Changed method name
        _, text = self._parse_literal_block_value(lines, start_line)  # Changed method name
        statement.parameters["text"] = text
        return start_line

# Example usage
def main():
    test_input = """
    Create New File
        name: test.py
        content:
        .def greet():
        # This comment is between literal block lines but doesn't affect them
        .    print("Hello")
        # Another comment that will be ignored
        .    return None
        
    Show Documentation
        description:
        .First line of documentation
        .Second line continues normally
        .Third line shows that comments don't break the block
        .Final line of the block
        
    Deploy Application
        /Infrastructure
            Provision Servers
                cloud: aws
                regions:
                - us-west-2
                - eu-central-1
                config:
                .server_count: 3
                .instance_type: t2.micro
                .environment: production
        Infrastructure/
    """
    
    parser = StatementParser()
    statements = parser.parse(test_input)
    
    if parser.errors:
        print("Parsing errors:")
        for error in parser.errors:
            print(error)
    else:
        print("Successfully parsed statements:")
        parser.print_statements(statements)

if __name__ == "__main__":
    main()