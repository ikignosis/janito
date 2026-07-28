"""
/show_tools_stats command handler - displays tool usage statistics.

Reads the per-tool invocation counters persisted by
:mod:`janito.tooling.tools_usage` in the ``tools_use.db`` SQLite database and
renders them as a `rich <https://github.com/Textualize/rich>`_ table, sorted
from the most-used tool to the least-used.
"""

from __future__ import annotations

from .base import CmdHandler
from .registry import register_command


class ShowToolsStatsCmdHandler(CmdHandler):
    """Command handler for the /show_tools_stats command."""

    @property
    def name(self) -> str:
        return "/show_tools_stats"

    def handle(self, shell, user_input: str) -> bool:
        """Handle the /show_tools_stats command."""
        if user_input.strip().lower() == self.name.lower():
            self._print_stats()
            return True
        return False

    def _build_table(self, uses: dict[str, int]):
        """Build a rich ``Table`` with the tool usage statistics.

        Args:
            uses: Mapping of tool name to usage count (as returned by
                ``tools_usage.get_all_tool_uses()``, already sorted from the
                most-used to the least-used tool).

        Returns:
            rich.table.Table: A table with rank, tool name, use count and
                percentage-share columns plus a total footer row.
        """
        from rich.table import Table

        total = sum(uses.values())

        table = Table(
            title="Tool Usage Statistics",
            title_style="bold",
            header_style="bold cyan",
            show_lines=False,
        )
        table.add_column("#", justify="right", style="dim", no_wrap=True)
        table.add_column("Tool", style="green", no_wrap=True)
        table.add_column("Uses", justify="right")
        table.add_column("%", justify="right", style="dim")

        for rank, (name, count) in enumerate(uses.items(), start=1):
            pct = (count / total * 100) if total else 0.0
            table.add_row(str(rank), name, str(count), f"{pct:.1f}%")

        # Footer row with the grand total, visually separated from the data.
        # ``add_section`` only exists on rich >= 13.2 (project allows >=10), so
        # fall back to a plain separator row on older versions.
        if hasattr(table, "add_section"):
            table.add_section()
        table.add_row("", "[bold]Total[/bold]", f"[bold]{total}[/bold]", "100.0%")

        return table

    def _print_stats(self) -> None:
        """Print the tool usage statistics table (or a friendly message)."""
        from rich.console import Console

        from janito.tooling.tools_usage import get_all_tool_uses, get_db_path

        console = Console()
        uses = get_all_tool_uses()

        if not uses:
            console.print("No tool usage recorded yet.")
            console.print(f"[dim](database: {get_db_path()})[/dim]")
            return

        table = self._build_table(uses)
        table.caption = f"Database: {get_db_path()}"
        table.caption_justify = "left"
        console.print(table)


# Register this handler
_handler = ShowToolsStatsCmdHandler()
register_command(_handler)
