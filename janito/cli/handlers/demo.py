from rich.console import Console
from janito.demo import DemoRunner
from janito.demo.data import get_demo_scenarios
from ..base import BaseCLIHandler

class DemoHandler(BaseCLIHandler):
    def handle(self):
        """Run demo scenarios"""
        runner = DemoRunner()

        # Add predefined scenarios
        for scenario in get_demo_scenarios():
            runner.add_scenario(scenario)

        # Preview and run scenarios
        self.console.print("\n[bold cyan]Demo Scenarios Preview:[/bold cyan]")
        runner.preview_changes()

        self.console.print("\n[bold cyan]Running Demo Scenarios:[/bold cyan]")
        runner.run_all()

        self.console.print("\n[green]Demo completed successfully![/green]")