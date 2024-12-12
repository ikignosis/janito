from enum import Enum
from dataclasses import dataclass
from typing import List, Dict, Any, Callable, Optional, Union
from pprint import pprint

class LineType(Enum):
    COMMENT = "COMMENT"
    STATEMENT = "STATEMENT"
    TEXT_BLOCK = "TEXT_BLOCK"
    KEY_VALUE = "KEY_VALUE"
    SECTION_START = "SECTION_START"
    SECTION_END = "SECTION_END"
    EMPTY = "EMPTY"

@dataclass
class Line:
    type: LineType
    content: Union[str, Dict[str, Any]]
    raw: str
    line_number: int
    indentation: int

@dataclass
class Section:
    name: str
    properties: Dict[str, str]
    content: List[Any]
    
    def get_text_content(self) -> str:
        """Helper method to extract text block content from a section"""
        return "\n".join(
            line.content for line in self.content 
            if isinstance(line, Line) and line.type == LineType.TEXT_BLOCK
        )

@dataclass
class StatementContext:
    """Context object passed to statement handlers"""
    statement: str
    parameters: Dict[str, str]
    sections: Dict[str, Section]
    line_number: int

class ParserError(Exception):
    """Custom exception for parser errors"""
    def __init__(self, message: str, line_number: int):
        self.line_number = line_number
        super().__init__(f"Line {line_number}: {message}")

class SSFParser:
    def __init__(self):
        self.current_line = 0
        self.statement_handlers: Dict[str, Callable[[StatementContext], None]] = {}
        self.current_statement_params: Dict[str, str] = {}
        
    def register_handler(self, statement_name: str, handler: Callable[[StatementContext], None]):
        """Register a handler for a specific statement name"""
        self.statement_handlers[statement_name] = handler
    
    def _parse_properties(self, prop_part: str) -> Dict[str, str]:
        """Helper method to parse section properties"""
        properties = {}
        current_key = None
        current_value = []
        
        # Handle quoted values with spaces
        in_quotes = False
        for part in prop_part.split():
            if '=' in part and not in_quotes:
                if current_key:
                    properties[current_key] = " ".join(current_value)
                key, value = part.split('=', 1)
                if value.startswith('"'):
                    if value.endswith('"'):
                        properties[key] = value[1:-1]
                    else:
                        current_key = key
                        current_value = [value[1:]]
                        in_quotes = True
                else:
                    properties[key] = value
            elif in_quotes:
                if part.endswith('"'):
                    current_value.append(part[:-1])
                    properties[current_key] = " ".join(current_value)
                    in_quotes = False
                else:
                    current_value.append(part)
                    
        return properties
    
    def parse_line(self, line: str) -> Line:
        """Parse a single line and determine its type and content."""
        self.current_line += 1
        
        # Calculate indentation before stripping
        indentation = len(line) - len(line.lstrip())
        line = line.strip()
        
        if not line:
            return Line(LineType.EMPTY, "", "", self.current_line, indentation)
            
        try:
            if line.startswith('#'):
                return Line(LineType.COMMENT, line[1:].strip(), line, self.current_line, indentation)
                
            if line.startswith('.'):
                return Line(LineType.TEXT_BLOCK, line[1:], line, self.current_line, indentation)
                
            if line.endswith('/'):
                section_name = line[:-1].strip()
                if not section_name:
                    raise ParserError("Empty section end tag", self.current_line)
                return Line(LineType.SECTION_END, section_name, line, self.current_line, indentation)
                
            if line.startswith('/'):
                base = line[1:].strip()
                if not base:
                    raise ParserError("Empty section start tag", self.current_line)
                    
                properties = {}
                if ' ' in base:
                    name_part, prop_part = base.split(' ', 1)
                    properties = self._parse_properties(prop_part)
                else:
                    name_part = base
                    
                return Line(LineType.SECTION_START, 
                           {"name": name_part, "properties": properties}, 
                           line, 
                           self.current_line,
                           indentation)
                
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip()
                if not key:
                    raise ParserError("Empty key in key-value pair", self.current_line)
                return Line(LineType.KEY_VALUE, 
                           {"key": key, "value": value.strip()}, 
                           line,
                           self.current_line,
                           indentation)
                
            return Line(LineType.STATEMENT, line, line, self.current_line, indentation)
            
        except Exception as e:
            if not isinstance(e, ParserError):
                raise ParserError(str(e), self.current_line) from e
            raise
            
    def parse(self, content: str) -> List[Any]:
        """Parse the entire SSF content."""
        self.current_line = 0  # Reset line counter
        lines = content.splitlines()
        parsed = []
        section_stack = []
        
        current_statement: Optional[Dict[str, Any]] = None
        
        def finish_current_statement():
            nonlocal current_statement
            if current_statement and current_statement["name"] in self.statement_handlers:
                context = StatementContext(
                    statement=current_statement["name"],
                    parameters=current_statement["parameters"],
                    sections=current_statement["sections"],
                    line_number=self.current_line
                )
                try:
                    self.statement_handlers[current_statement["name"]](context)
                except Exception as e:
                    raise ParserError(f"Handler error for statement '{current_statement['name']}': {str(e)}", 
                                    self.current_line) from e
                parsed.append(current_statement)
            current_statement = None
        
        for line in lines:
            parsed_line = self.parse_line(line)
            
            if parsed_line.type == LineType.EMPTY:
                continue
                
            # Validate section nesting
            if parsed_line.type == LineType.SECTION_END:
                if not section_stack:
                    raise ParserError(f"Unexpected section end '{parsed_line.content}'", parsed_line.line_number)
                if section_stack[-1].name != parsed_line.content:
                    raise ParserError(
                        f"Mismatched section end. Expected '{section_stack[-1].name}/', got '{parsed_line.content}/'",
                        parsed_line.line_number
                    )
            
            # Handle statements and their parameters
            if parsed_line.type == LineType.STATEMENT:
                finish_current_statement()
                
                current_statement = {
                    "type": "statement",
                    "name": parsed_line.content,
                    "parameters": {},
                    "sections": {},
                    "line_number": parsed_line.line_number
                }
                
            elif parsed_line.type == LineType.KEY_VALUE:
                if current_statement:
                    current_statement["parameters"][parsed_line.content["key"]] = parsed_line.content["value"]
                else:
                    raise ParserError("Key-value pair outside of statement", parsed_line.line_number)
                
            elif parsed_line.type == LineType.SECTION_START:
                new_section = Section(
                    name=parsed_line.content["name"],
                    properties=parsed_line.content["properties"],
                    content=[]
                )
                
                if section_stack:
                    section_stack[-1].content.append(new_section)
                else:
                    if current_statement:
                        current_statement["sections"][new_section.name] = new_section
                    else:
                        parsed.append(new_section)
                    
                section_stack.append(new_section)
                
            elif parsed_line.type == LineType.SECTION_END:
                section_stack.pop()
                    
            else:  # COMMENT or TEXT_BLOCK
                if section_stack:
                    section_stack[-1].content.append(parsed_line)
                else:
                    if current_statement:
                        # Store top-level comments/text within current statement
                        if "content" not in current_statement:
                            current_statement["content"] = []
                        current_statement["content"].append(parsed_line)
                    else:
                        parsed.append(parsed_line)
        
        # Check for unclosed sections
        if section_stack:
            raise ParserError(
                f"Unclosed section: '{section_stack[-1].name}'", 
                self.current_line
            )
        
        # Process final statement if exists
        finish_current_statement()
            
        return parsed
    

def main():
    """Example usage of the SSF Parser"""
    
    # Define some example handlers
    def create_file_handler(context: StatementContext):
        print(f"\nProcessing Create File statement:")
        print(f"  Path: {context.parameters.get('Path')}")
        print(f"  Mode: {context.parameters.get('Mode', 'default')}")
        
        if 'Content' in context.sections:
            content = context.sections['Content'].get_text_content()
            print("  Content:")
            for line in content.split('\n'):
                print(f"    {line}")

    def modify_file_handler(context: StatementContext):
        print(f"\nProcessing Modify File statement:")
        print(f"  Path: {context.parameters.get('Path')}")
        
        if 'Modifications' in context.sections:
            mods = context.sections['Modifications']
            print("  Modifications:")
            for item in mods.content:
                if isinstance(item, Section):
                    print(f"    - {item.name} modification")
                    if item.properties:
                        print(f"      Properties: {item.properties}")
                    if len(item.content) > 0:
                        print("      Content:")
                        for subitem in item.content:
                            if isinstance(subitem, Section):
                                content = subitem.get_text_content()
                                print(f"        {subitem.name}:")
                                for line in content.split('\n'):
                                    print(f"          {line}")

    # Create parser instance and register handlers
    parser = SSFParser()
    parser.register_handler("Create File", create_file_handler)
    parser.register_handler("Modify File", modify_file_handler)

    # Example SSF content demonstrating various features
    test_content = """
# This is a comment
Create File
    Path: /path/to/test.py
    Mode: write
    /Content
    .def example_function():
    .    # This is a nested comment
    .    print("Hello, World!")
    .    
    .    for i in range(5):
    .        print(f"Count: {i}")
    Content/

# Another comment
Modify File
    Path: /path/to/test.py
    /Modifications
        /replace target="function" mode="exact"
            /text
                .def old_function():
                .    return True
            text/
            /with
                .def new_function():
                .    return False
            with/
        replace/
        
        /append position="end"
            /text
                .# Appended content
                .print("Done!")
            text/
        append/
    Modifications/
"""

    try:
        # Parse the content
        print("Parsing SSF content...")
        result = parser.parse(test_content)
        
        print("\nComplete parse tree:")
        pprint(result, indent=2, width=80, depth=None)
        
    except ParserError as e:
        print(f"Parser error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")

if __name__ == "__main__":
    main()