"""
/skills command handler - displays all available skills.
"""

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


def _truncate(description: str, length: int = 60) -> str:
    """Truncate a skill description to ``length`` chars for display."""
    if len(description) > length:
        return description[: length - 3] + "..."
    return description


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
        """Print information about all available skills."""
        skills = _load_skills()

        print()
        print("=" * 60)
        print("Available Skills")
        print("=" * 60)

        if not skills:
            print("  No skills installed.")
            print()
            print("  Home skills:  <config_dir>/skills")
            print("  Local skills: .janito/skills (in the current directory)")
            print()
            print("  Use `janito --install-skill <github-url>` to install a skill.")
            print("=" * 60)
            print()
            return

        home_skills = [s for s in skills if s["source"] == "home"]
        local_skills = [s for s in skills if s["source"] == "local"]

        if home_skills:
            print("\n[Home Skills]")
            print("-" * 40)
            for skill in home_skills:
                name = skill["name"]
                description = _truncate(skill["description"])
                print(f"  {name:<25} {description}")

        if local_skills:
            print("\n[Local Skills]")
            print("-" * 40)
            for skill in local_skills:
                name = skill["name"]
                description = _truncate(skill["description"])
                print(f"  {name:<25} {description}")

        # Summary
        total = len(skills)
        print()
        print(
            f"Total: {total} skill(s) "
            f"({len(home_skills)} home, {len(local_skills)} local)"
        )
        print("=" * 60)
        print()


# Register this handler
_handler = SkillsCmdHandler()
register_command(_handler)
