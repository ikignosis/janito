# models.py
from dataclasses import dataclass
from typing import Dict, List, Union, Optional, Tuple
from enum import Enum

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