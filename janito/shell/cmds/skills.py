"""
/skills command handler - displays all available skills.
"""

from rich.console import Console
from rich.table import Table

from .base import CmdHandler
from .registry import register_command


def _load_skills():
    """Load skills from the skills provider."""
    try:
        from janito.tooling.skills_provider import get_skills_provider

        provider = get_skills_provider()
        return provider.list_skills()
    except Exception as e:
        print(f"Warning: Could not load skills: {e}")
        return []


def _skills_table(title: str, skills: list[dict]) -> None:
    """Print a Name/Description table for a group of skills."""
    table = Table(
        title=title,
        title_style="bold",
        header_style="bold cyan",
    )
    table.add_column("Name", style="green", no_wrap=True)
    table.add_column("Description", overflow="fold")
    for skill in skills:
        # Keep the complete description; Rich wraps it to fit the terminal.
        table.add_row(skill["name"], skill["description"])
    Console(markup=False).print(table)


class SkillsCmdHandler(CmdHandler):
    """Command handler for /skills command."""

    @property
    def name(self) -> str:
        return "/skills"

    def handle(self, shell, user_input: str) -> bool:
        """Handle the /skills command."""
        if user_input.lower() == self.name.lower():
            self._print_skills()
            return True
        return False

    def _print_skills(self) -> None:
        """Print information about all available skills as rich tables."""
        skills = _load_skills()

        if not skills:
            console = Console(markup=False)
            table = Table(
                title="Available Skills",
                title_style="bold",
                header_style="bold cyan",
                show_header=False,
                box=None,
                pad_edge=False,
            )
            table.add_column("Key", style="green", no_wrap=True)
            table.add_column("Value", overflow="fold")
            table.add_row("Status", "No skills installed.")
            table.add_row("Home skills", "<config_dir>/skills")
            table.add_row("Agent skills", ".agents/skills (in the current directory)")
            table.add_row("Local skills", ".janito/skills (in the current directory)")
            table.add_row(
                "Install",
                "Use `janito --install-skill <github-url>` to install a skill.",
            )
            console.print(table)
            return

        home_skills = [s for s in skills if s["source"] == "home"]
        agent_skills = [s for s in skills if s["source"] == "agents"]
        local_skills = [s for s in skills if s["source"] == "local"]

        if home_skills:
            _skills_table("Home Skills", home_skills)

        # Agent skills are a distinct discovery source (``.agents/skills``).
        # They must not be silently omitted from the shell output or summary.
        if agent_skills:
            _skills_table("Agent Skills", agent_skills)

        if local_skills:
            _skills_table("Local Skills", local_skills)

        # Summary
        total = len(skills)
        summary = Table(
            title="Summary",
            title_style="bold",
            header_style="bold cyan",
            show_header=False,
            box=None,
            pad_edge=False,
        )
        summary.add_column("Key", style="green", no_wrap=True)
        summary.add_column("Value")
        # Keep the compact two-source format when no agent skills are present
        # for backwards compatibility, but report all three sources when they
        # are in use.
        if agent_skills:
            source_summary = (
                f"{len(home_skills)} home, {len(agent_skills)} agents, "
                f"{len(local_skills)} local"
            )
        else:
            source_summary = f"{len(home_skills)} home, {len(local_skills)} local"
        summary.add_row("Total", f"{total} skill(s) ({source_summary})")
        Console(markup=False).print(summary)


# Register this handler
_handler = SkillsCmdHandler()
register_command(_handler)
