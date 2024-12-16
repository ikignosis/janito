from typing import Dict, List
from .scenarios import DemoScenario
from .mock_data import get_mock_changes

def get_demo_scenarios() -> List[DemoScenario]:
    """Get list of predefined demo scenarios"""
    return [
        DemoScenario(
            name="File Operations Demo",
            description="Demonstrate various file operations with change viewer",
            changes=get_mock_changes()
        )
    ]