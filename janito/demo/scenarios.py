from dataclasses import dataclass
from typing import List, Dict, Optional
from rich.text import Text
from pathlib import Path
from .operations import MockOperation
from .mock_data import get_mock_changes

@dataclass
class DemoScenario:
    name: str
    description: str
    changes: List[MockOperation]

    def get_preview(self) -> Text:
        """Get a preview of the changes"""
        text = Text()
        text.append(f"Description: {self.description}\n\n", style="cyan")

        # Group changes by operation
        by_operation = {}
        for change in self.changes:
            if change.operation not in by_operation:
                by_operation[change.operation] = []
            by_operation[change.operation].append(change)

        # Show changes grouped by operation
        for operation_type, changes in by_operation.items():
            text.append(f"\n{operation_type.name.title()} Operations:\n", style="yellow")
            for change in changes:
                text.append(f"• {change.name}\n", style="white")

        return text