from typing import List, Optional
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from .scenarios import DemoScenario
from .operations import MockOperationType
from ..change.viewer import preview_all_changes
from ..change.parser import FileChange, ChangeOperation

class DemoRunner:
    def __init__(self):
        self.console = Console()
        self.scenarios: List[DemoScenario] = []

    def add_scenario(self, scenario: DemoScenario) -> None:
        """Add a demo scenario to the runner"""
        self.scenarios.append(scenario)

    def run_all(self) -> None:
        """Run all registered demo scenarios"""
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console
        ) as progress:
            for scenario in self.scenarios:
                task = progress.add_task(f"Running scenario: {scenario.name}")
                self.preview_changes(scenario)
                progress.update(task, completed=True)

    def preview_changes(self, scenario: Optional[DemoScenario] = None) -> None:
        """Preview changes for a scenario using change viewer"""
        if scenario is None:
            if not self.scenarios:
                self.console.print("[yellow]No scenarios to preview[/yellow]")
                return
            scenario = self.scenarios[0]

        # Convert mock changes to FileChange objects
        changes = []
        for mock in scenario.changes:
            # Map mock operation type to ChangeOperation
            operation_map = {
                MockOperationType.CREATE: ChangeOperation.CREATE_FILE,
                MockOperationType.MODIFY: ChangeOperation.MODIFY_FILE,
                MockOperationType.REMOVE: ChangeOperation.REMOVE_FILE
            }
            operation = operation_map[mock.operation_type]
            change = FileChange(
                operation=operation,
                name=Path(mock.name),
                content=mock.content if hasattr(mock, 'content') else None,
                original_content=mock.original_content if hasattr(mock, 'original_content') else None
            )
            changes.append(change)

        # Show changes using change viewer
        preview_all_changes(self.console, changes)