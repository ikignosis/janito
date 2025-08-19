"""
CLI Command: List available system prompt profiles (default and user-specific)
"""

from pathlib import Path
import importlib.resources as resources
from rich.console import Console
from rich.table import Table


_PREFIX = "system_prompt_template_"
_SUFFIX = ".txt.j2"


def _extract_profile_name(filename: str) -> str:
    """Return the human-readable profile name from template file name."""
    # Remove prefix & suffix and convert underscores back to spaces
    if filename.startswith(_PREFIX):
        filename = filename[len(_PREFIX) :]
    if filename.endswith(_SUFFIX):
        filename = filename[: -len(_SUFFIX)]

    # Convert to title case for consistent capitalization, but handle common acronyms
    name = filename.replace("_", " ")

    # Convert to proper title case with consistent capitalization
    name = filename.replace("_", " ")

    # Handle special cases and acronyms
    special_cases = {
        "python": "Python",
        "tools": "Tools",
        "model": "Model",
        "context": "Context",
        "developer": "Developer",
        "analyst": "Analyst",
        "conversation": "Conversation",
        "without": "Without",
    }

    words = name.split()
    capitalized_words = []
    for word in words:
        lower_word = word.lower()
        if lower_word in special_cases:
            capitalized_words.append(special_cases[lower_word])
        else:
            capitalized_words.append(word.capitalize())

    return " ".join(capitalized_words)


def _gather_default_profiles():
    """Return list of built-in profile names bundled with janito."""
    profiles = []
    try:
        package_files = resources.files("janito.agent.templates.profiles")
        for path in package_files.iterdir():
            name = path.name
            if name.startswith(_PREFIX) and name.endswith(_SUFFIX):
                profiles.append(_extract_profile_name(name))
    except Exception:
        # If for some reason the resources are not available fall back to empty list
        pass
    return sorted(profiles, key=str.lower)


def _gather_user_profiles():
    """Return list of user-defined profile names from ~/.janito/profiles directory."""
    user_dir = Path.home() / ".janito" / "profiles"
    profiles = []
    if user_dir.exists() and user_dir.is_dir():
        for path in user_dir.iterdir():
            if (
                path.is_file()
                and path.name.startswith(_PREFIX)
                and path.name.endswith(_SUFFIX)
            ):
                profiles.append(_extract_profile_name(path.name))
    return sorted(profiles, key=str.lower)


def _print_profiles_table(default_profiles, user_profiles):
    console = Console()
    table = Table(title="Available System Prompt Profiles", box=None, show_lines=False)
    table.add_column("Profile Name", style="cyan", no_wrap=False)
    table.add_column("Source", style="magenta", no_wrap=True)

    for p in default_profiles:
        table.add_row(p, "default")
    for p in user_profiles:
        table.add_row(p, "user")

    console.print(table)


def handle_list_profiles(args=None):
    """Entry point for the --list-profiles CLI flag."""
    default_profiles = _gather_default_profiles()
    user_profiles = _gather_user_profiles()

    if not default_profiles and not user_profiles:
        print("No profiles found.")
        return

    _print_profiles_table(default_profiles, user_profiles)
    return
