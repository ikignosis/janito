from dataclasses import dataclass, field
from typing import List, Dict, Union, Optional

@dataclass
class KeyValDict:
    """
    Represents a dictionary of key/value pairs.
    """
    data: Dict[str, Union[str, List]] = field(default_factory=dict)

@dataclass
class LiteralBlock:
    """
    Represents a block of literal text.
    """
    content: str = ""

@dataclass
class Statement:
    """
    Represents a statement, which can have parameters (key/value pairs, lists, literal blocks)
    and associated blocks.
    """
    name: str
    kv: Optional[KeyValDict] = None
    text: Optional[LiteralBlock] = None
    list_items: Optional[List[str]] = None
    blocks: Optional[List["Block"]] = None

@dataclass
class Block:
    """
    Represents a block, which groups related parameters or sub-blocks.
    Blocks can only contain parameters (key/value pairs, lists, or literal blocks) or other blocks.
    """
    name: Optional[str] = None
    kv: Optional[KeyValDict] = None
    text: Optional[LiteralBlock] = None
    list_items: Optional[List[str]] = None
    blocks: Optional[List["Block"]] = field(default_factory=list)
