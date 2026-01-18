"""CLI Command: List available system prompt profiles.

This uses janito.agent.system_prompt.SystemPromptTemplateManager to list profiles
and apply source precedence + deduplication.
"""

from rich.console import Console
from rich.table import Table

from janito.agent.system_prompt import SystemPromptTemplateManager


def _print_profiles_table(profiles):
    console = Console()
    table = Table(title="Available System Prompt Profiles", box=None, show_lines=False)
    table.add_column("Profile Name", style="cyan", no_wrap=False)
    table.add_column("Source", style="magenta", no_wrap=True)

    for p in profiles:
        table.add_row(p.name, p.source)

    console.print(table)


def handle_list_profiles(args=None):
    """Entry point for the --list-profiles CLI flag."""
    spm = SystemPromptTemplateManager(templates_dir=None)
    profiles = spm.list_profiles()

    if not profiles:
        print("No profiles found.")
        return

    _print_profiles_table(profiles)
    return
