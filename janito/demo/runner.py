from typing import List, Optional
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from .scenarios import DemoScenario
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
                self._preview_scenario(scenario)
                progress.update(task, completed=True)

    def preview_changes(self, scenario: DemoScenario) -> None:
        """Preview changes for a scenario using change viewer"""
        # Convert mock changes to FileChange objects
        changes = []
        for mock in scenario.changes:
            operation = ChangeOperation[mock.operation.upper()]
            change = FileChange(
                operation=operation,
                name=Path(mock.name),
                content=mock.content,
                original_content=mock.original_content
            )
            changes.append(change)

        # Show changes using change viewer
        preview_all_changes(self.console, changes)

    def _preview_scenario(self, scenario: DemoScenario) -> None:
        """Preview changes for a scenario using change viewer"""
        self.preview_changes(scenario)