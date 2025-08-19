"""
CLI Command: List available LLM drivers and their dependencies
"""

import importlib
import sys
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

console = Console()


def _detect_dependencies_from_content(content, class_name):
    """Detect dependencies from module content."""
    dependencies = []

    if "import openai" in content or "from openai" in content:
        dependencies.append("openai")
    if "import zai" in content or "from zai" in content:
        dependencies.append("zai")
    if "import anthropic" in content or "from anthropic" in content:
        dependencies.append("anthropic")
    if "import google" in content or "from google" in content:
        dependencies.append("google-generativeai")

    # Remove openai from zai driver dependencies
    if "ZAIModelDriver" in class_name and "openai" in dependencies:
        dependencies.remove("openai")

    return dependencies


def _check_dependency_status(dependencies):
    """Check if dependencies are available."""
    if not dependencies:
        return ["No external dependencies"]

    dep_status = []
    for dep in dependencies:
        try:
            importlib.import_module(dep)
            dep_status.append(f"✅ {dep}")
        except ImportError:
            dep_status.append(f"❌ {dep}")

    return dep_status


def _get_single_driver_info(module_path, class_name):
    """Get information for a single driver."""
    try:
        module = importlib.import_module(module_path)
        driver_class = getattr(module, class_name)

        available = getattr(driver_class, "available", True)
        unavailable_reason = getattr(driver_class, "unavailable_reason", None)

        # Read module file to detect imports
        module_file = Path(module.__file__)
        with open(module_file, "r", encoding="utf-8") as f:
            content = f.read()

        dependencies = _detect_dependencies_from_content(content, class_name)
        dep_status = _check_dependency_status(dependencies)

        return {
            "name": class_name,
            "available": available,
            "reason": unavailable_reason,
            "dependencies": dep_status,
        }

    except (ImportError, AttributeError) as e:
        return {
            "name": class_name,
            "module": module_path,
            "available": False,
            "reason": str(e),
            "dependencies": ["❌ Module not found"],
        }


def get_driver_info():
    """Get information about all available drivers."""
    drivers = []

    # Define known driver modules
    driver_modules = [
        ("janito.drivers.openai.driver", "OpenAIModelDriver"),
        ("janito.drivers.azure_openai.driver", "AzureOpenAIModelDriver"),
        ("janito.drivers.zai.driver", "ZAIModelDriver"),
        ("janito.drivers.cerebras.driver", "CerebrasModelDriver"),
    ]

    for module_path, class_name in driver_modules:
        driver_info = _get_single_driver_info(module_path, class_name)
        drivers.append(driver_info)

    return drivers


def _create_driver_table(drivers):
    """Create and populate the drivers table."""
    table = Table(title="Available LLM Drivers")
    table.add_column("Driver", style="cyan", no_wrap=True)
    table.add_column("Status", style="bold")
    table.add_column("Dependencies", style="yellow")

    for driver in drivers:
        name = driver["name"]

        if driver["available"]:
            status = "[green]✅ Available[/green]"
            if driver["reason"]:
                status = f"[yellow]⚠️ Available ({driver['reason']})[/yellow]"
        else:
            status = f"[red]❌ Unavailable[/red]"
            if driver["reason"]:
                status = f"[red]❌ {driver['reason']}[/red]"

        deps = "\n".join(driver["dependencies"])
        table.add_row(name, status, deps)

    return table


def _get_missing_dependencies(drivers):
    """Get list of missing dependencies."""
    missing_deps = []
    for driver in drivers:
        for dep_status in driver["dependencies"]:
            if dep_status.startswith("❌"):
                dep_name = dep_status.split()[1]
                if dep_name not in missing_deps:
                    missing_deps.append(dep_name)
    return missing_deps


def handle_list_drivers(args=None):
    """List all available LLM drivers with their status and dependencies."""
    drivers = get_driver_info()

    if not drivers:
        console.print("[red]No drivers found[/red]")
        return

    table = _create_driver_table(drivers)
    console.print(table)

    # Installation help - only show for missing dependencies
    missing_deps = _get_missing_dependencies(drivers)
    if missing_deps:
        console.print(
            f"\n[dim]💡 Install missing deps: pip install {' '.join(missing_deps)}[/dim]"
        )


if __name__ == "__main__":
    handle_list_drivers()
