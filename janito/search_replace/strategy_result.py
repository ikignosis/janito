from dataclasses import dataclass
from typing import Optional

@dataclass
class StrategyResult:
    """Encapsulates the result of a strategy match attempt."""
    success: bool
    strategy_name: Optional[str] = None
    match_position: Optional[int] = None
    file_type: Optional[str] = None