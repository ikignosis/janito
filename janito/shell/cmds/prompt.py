"""
/prompt command handler - displays the current system prompt.
"""

from .base import CmdHandler
from .registry import register_command


class PromptCmdHandler(CmdHandler):
    """Command handler for /prompt command."""

    @property
    def name(self) -> str:
        return "/prompt"

    def handle(self, shell, user_input: str) -> bool:
        """Handle the /prompt command."""
        if user_input.lower() == self.name.lower():
            self._print_prompt(shell)
            return True
        return False

    def _print_prompt(self, shell) -> None:
        """Print the current system prompt."""
        from rich.console import Console
        from rich.table import Table

        from janito.system_prompt import (
            get_system_prompt_sections,
            get_system_prompt_with_skills,
        )

        # Get the actual system prompt from the shell
        effective_prompt = shell.get_system_prompt()

        if effective_prompt is None:
            Console(markup=False).print(
                "No system prompt is active (--no-system-prompt)"
            )
            return

        if effective_prompt == get_system_prompt_with_skills():
            # Default prompt: show each section as a rich table row with its
            # name, line count and content.
            table = Table(
                title="System Prompt - Default (with Skills)",
                title_style="bold",
                header_style="bold cyan",
            )
            table.add_column("Section", style="green", no_wrap=True)
            table.add_column("Lines", justify="right")
            table.add_column("Content", overflow="fold")
            for name, text in get_system_prompt_sections():
                body = text.strip()
                line_count = len(body.splitlines()) if body else 0
                table.add_row(name, str(line_count), body)
            Console(markup=False).print(table)
            return

        # Custom prompt (-S): detect which prompt type is active.
        if "Gmail" in effective_prompt:
            prompt_type = "Gmail Mode"
        elif "OneDrive" in effective_prompt:
            prompt_type = "OneDrive Mode"
        else:
            prompt_type = "Default"

        table = Table(
            title=f"System Prompt - {prompt_type}",
            title_style="bold",
            header_style="bold cyan",
            show_header=False,
        )
        table.add_column("Content", overflow="fold")
        table.add_row(effective_prompt.strip())
        Console(markup=False).print(table)


# Register this handler
_handler = PromptCmdHandler()
register_command(_handler)
