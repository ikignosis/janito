from dataclasses import dataclass, field
from typing import List, Dict, Union, Optional

@dataclass
class KeyValuePair:
    key: str
    value: Union[str, List[str], "LiteralBlock"]

@dataclass
class LiteralBlock:
    lines: List[str]

@dataclass
class ListItem:
    value: str

@dataclass
class Block:
    name: str
    parameters: Dict[str, Union[str, List[str], LiteralBlock]] = field(default_factory=dict)
    blocks: List["Block"] = field(default_factory=list)

@dataclass
class Statement:
    name: str
    parameters: Dict[str, Union[str, List[str], LiteralBlock]] = field(default_factory=dict)
    blocks: List[Block] = field(default_factory=list)

class ClearStatementParser:
    def __init__(self, content: str):
        self.lines = content.splitlines()
        self.current_line = 0

    def parse(self) -> List[Statement]:
        statements = []
        while self.current_line < len(self.lines):
            line = self.lines[self.current_line].strip()
            if not line or line.startswith("#"):
                self.current_line += 1
                continue
            if ":" in line:
                # Handle key/value pairs
                key, value = map(str.strip, line.split(":", 1))
                if self.current_line + 1 < len(self.lines) and self.lines[self.current_line + 1].startswith("."):
                    # Multi-line literal block
                    literal_lines = []
                    self.current_line += 1
                    while self.current_line < len(self.lines) and self.lines[self.current_line].startswith("."):
                        literal_lines.append(self.lines[self.current_line][1:].strip())
                        self.current_line += 1
                    statements[-1].parameters[key] = LiteralBlock(literal_lines)
                elif self.current_line + 1 < len(self.lines) and self.lines[self.current_line + 1].startswith("-"):
                    # List
                    items = []
                    self.current_line += 1
                    while self.current_line < len(self.lines) and self.lines[self.current_line].startswith("-"):
                        items.append(self.lines[self.current_line][1:].strip())
                        self.current_line += 1
                    statements[-1].parameters[key] = items
                else:
                    # Single-line value
                    statements[-1].parameters[key] = value
                    self.current_line += 1
            elif line.startswith("/"):
                # Handle blocks
                if line == "/":
                    # End of block
                    self.current_line += 1
                    continue
                block_name = line[1:]
                block = Block(name=block_name)
                self.current_line += 1
                while self.current_line < len(self.lines) and not self.lines[self.current_line].strip() == "/":
                    if self.lines[self.current_line].strip().startswith("/"):
                        # Nested block
                        nested_block = self._parse_block()
                        block.blocks.append(nested_block)
                    else:
                        # Parameters within the block
                        key, value = map(str.strip, self.lines[self.current_line].split(":", 1))
                        block.parameters[key] = value
                        self.current_line += 1
                statements[-1].blocks.append(block)
                self.current_line += 1
            else:
                # Handle statements
                statement = Statement(name=line)
                statements.append(statement)
                self.current_line += 1
        return statements

    def _parse_block(self) -> Block:
        line = self.lines[self.current_line].strip()
        block_name = line[1:]
        block = Block(name=block_name)
        self.current_line += 1
        while self.current_line < len(self.lines) and not self.lines[self.current_line].strip() == "/":
            if self.lines[self.current_line].strip().startswith("/"):
                # Nested block
                nested_block = self._parse_block()
                block.blocks.append(nested_block)
            else:
                # Parameters within the block
                key, value = map(str.strip, self.lines[self.current_line].split(":", 1))
                block.parameters[key] = value
                self.current_line += 1
        self.current_line += 1
        return block

# Example usage
content = """
Deploy Application
    name: my-app
    version: 1.0.0
    /Environment
        region: us-west-2
        /Resources
            - EC2
            - RDS
            /Security
                firewall:
                .allow: 80
                .allow: 443
                .deny: all
            /
        /
    /
"""

parser = ClearStatementParser(content)
statements = parser.parse()
for statement in statements:
    print(statement)