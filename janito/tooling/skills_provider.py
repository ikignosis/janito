"""
Skills provider for discovering and loading skills from the filesystem.

Based on Agent Skills progressive disclosure pattern:
1. Advertise (~100 tokens per skill) - names and descriptions in system prompt
2. Load (< 5000 tokens) - full SKILL.md content when skill is activated
3. Read resources - supplementary files when needed

Skills are discovered from multiple search paths:
- **Home skills** – ``<config_dir>/skills`` (default ``~/.janito/skills``)
- **Agent skills** – ``.agents/skills`` in the current working directory
- **Local skills** – ``.janito/skills`` in the current working directory

Each ``Skill`` tracks its own filesystem ``path``, so resources are always
loaded from the correct directory regardless of whether the skill lives in the
home, ``.agents`` or local ``.janito`` directory.  When a skill name exists in
multiple locations the **local** copy takes precedence, making it easy to override a
globally installed skill with a project-specific variant.
"""

from pathlib import Path
from typing import Any

from janito.config_dir import get_config_dir
from janito.tooling.reporter import report_error, report_result, report_start


def get_default_skills_dir() -> Path:
    """Get the default (home) skills directory (honors -c/--config-dir)."""
    return get_config_dir() / "skills"


def get_agents_skills_dir() -> Path:
    """Get the project agent skills directory (``.agents/skills`` in CWD)."""
    return Path.cwd() / ".agents" / "skills"


def get_local_skills_dir() -> Path:
    """Get the local skills directory (``.janito/skills`` in the CWD)."""
    return Path.cwd() / ".janito" / "skills"


# Default skills directory (at import time). Retained for backward compatibility;
# prefer :func:`get_default_skills_dir` which honors the -c/--config-dir override.
DEFAULT_SKILLS_DIR = get_default_skills_dir()


class Skill:
    """Represents a discovered skill.

    Attributes:
        name: Skill name (directory name).
        path: Filesystem path to the skill directory.
        source: Where the skill was found – ``"home"``, ``"agents"`` or
            ``"local"``.
        description: Short description extracted from SKILL.md.
        content: Cached SKILL.md content (populated by :meth:`load_content`).
        resources: Mapping of resource file name → path.
    """

    def __init__(
        self,
        name: str,
        path: Path,
        description: str = "",
        content: str = "",
        source: str = "home",
    ):
        self.name = name
        self.path = path
        self.source = source
        self.description = description
        self.content = content
        self.resources: dict[str, Path] = {}

        # Discover resources in the skill directory
        self._discover_resources()

    def _discover_resources(self):
        """Scan skill directory for additional resources."""
        if not self.path.exists():
            return

        for item in self.path.iterdir():
            if item.is_file() and item.name != "SKILL.md":
                self.resources[item.name] = item

    def load_content(self) -> str:
        """Load the full SKILL.md content."""
        skill_md = self.path / "SKILL.md"
        if skill_md.exists():
            with open(skill_md, encoding="utf-8") as f:
                self.content = f.read()
        return self.content

    def get_resource(self, resource_name: str) -> str | None:
        """Get the content of a skill resource.

        Args:
            resource_name: Name of the resource file

        Returns:
            Content of the resource file, or None if not found
        """
        resource_path = self.path / resource_name
        if resource_path.exists() and resource_path.is_file():
            try:
                with open(resource_path, encoding="utf-8") as f:
                    return f.read()
            except Exception:
                return None
        return None


class SkillsProvider:
    """
    Discovers and manages skills from filesystem directories.

    Searches configured paths recursively (up to two levels deep)
    for SKILL.md files.

    By default three search roots are used:

    1. **Home** – ``<config_dir>/skills`` (global, user-installed skills).
    2. **Agent** – ``.agents/skills`` in the current working directory
       (project-specific agent skills).
    3. **Local** – ``.janito/skills`` in the current working directory
       (project-specific skills).

    Project-local skills take precedence over home skills with the same name;
    ``.janito/skills`` takes precedence over ``.agents/skills`` when both
    provide a skill with the same name.
    """

    def __init__(self, skill_paths: list[Path] | list[tuple[Path, str]] = None):
        """
        Initialize the skills provider.

        Args:
            skill_paths: Search paths for skills.  Each entry may be either a
                bare :class:`~pathlib.Path` (defaults to source ``"home"``)
                or a ``(path, source)`` tuple where *source* is a short label
                such as ``"home"``, ``"agents"`` or ``"local"``.

                When ``None`` the default search paths are used::

                    [(get_default_skills_dir(), "home"),
                     (get_agents_skills_dir(),  "agents"),
                     (get_local_skills_dir(),   "local")]
        """
        if skill_paths is None:
            skill_paths = [
                (get_default_skills_dir(), "home"),
                (get_agents_skills_dir(), "agents"),
                (get_local_skills_dir(), "local"),
            ]

        # Normalise to a list of (Path, source) tuples
        self.skill_paths: list[tuple[Path, str]] = []
        for entry in skill_paths:
            if isinstance(entry, tuple):
                self.skill_paths.append((Path(entry[0]), entry[1]))
            else:
                self.skill_paths.append((Path(entry), "home"))

        self._skills: dict[str, Skill] = {}
        self._discover_skills()

    def _discover_skills(self):
        """Scan all skill paths for SKILL.md files.

        Paths are searched in order.  When a skill name appears in more than
        one path the *last* one processed wins.  ``skill_paths`` is ordered
        ``[home, local]`` so that **local skills override home skills**.
        """
        for base_path, source in self.skill_paths:
            if not base_path.exists():
                continue

            # Search up to 2 levels deep for SKILL.md files
            for level1 in base_path.iterdir():
                if not level1.is_dir():
                    continue

                skill_md = level1 / "SKILL.md"
                if skill_md.exists():
                    # It's a skill directory
                    self._add_skill(level1.name, level1, source)
                    continue

                # Check one more level deep
                for level2 in level1.iterdir():
                    if not level2.is_dir():
                        continue
                    skill_md = level2 / "SKILL.md"
                    if skill_md.exists():
                        self._add_skill(level2.name, level2, source)

    def _add_skill(self, name: str, path: Path, source: str = "home"):
        """Add a skill to the provider.

        Args:
            name: Skill name (directory name).
            path: Path to the skill directory.
            source: ``"home"`` or ``"local"`` – where the skill was found.
        """
        # Extract description from SKILL.md if available
        description = ""
        skill_md = path / "SKILL.md"
        if skill_md.exists():
            try:
                with open(skill_md, encoding="utf-8") as f:
                    content = f.read()
                    # Extract description from first paragraph
                    description = self._extract_description(content)
            except Exception:
                pass

        self._skills[name] = Skill(name, path, description, source=source)

    def _extract_description(self, content: str) -> str:
        """Extract a short description from SKILL.md content."""
        if not content:
            return ""

        # Skip YAML front matter if present
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                content = parts[2].strip()

        # Get first paragraph (non-empty lines)
        lines = content.split("\n")
        description_lines = []
        for line in lines:
            line = line.strip()
            if line.startswith("#"):
                continue  # Skip headers
            if line.startswith("```"):
                continue  # Skip code blocks
            if line:
                description_lines.append(line)
            if len(description_lines) >= 2:
                break

        # Keep the complete extracted description.  The shell/UI is
        # responsible for wrapping it to fit the available display width.
        return " ".join(description_lines)

    def get_skill(self, name: str) -> Skill | None:
        """Get a skill by name."""
        return self._skills.get(name)

    def list_skills(self) -> list[dict[str, str]]:
        """List all discovered skills.

        Returns:
            List of dicts with ``name``, ``description``, ``path`` and
            ``source`` for each skill.
        """
        result = []
        for name, skill in sorted(self._skills.items()):
            result.append(
                {
                    "name": name,
                    "description": skill.description or "No description",
                    "path": str(skill.path),
                    "source": skill.source,
                }
            )
        return result

    def get_advertisement(self) -> str:
        """
        Generate the skills advertisement section for system prompt.

        Returns:
            String with skill names and descriptions (~100 tokens per skill)
        """
        skills = self.list_skills()

        if not skills:
            return ""

        lines = [
            "## Available Skills",
            "Use these skills when the user's request matches their description:",
            "",
        ]

        for skill in skills:
            lines.append(f"- **{skill['name']}**: {skill['description']}")

        return "\n".join(lines)

    def get_skill_tool_schemas(self) -> list[dict[str, Any]]:
        """
        Get tool schemas for skill operations.

        Returns:
            List of tool schemas for load_skill and read_skill_resource
        """
        return [
            {
                "type": "function",
                "function": {
                    "name": "load_skill",
                    "description": (
                        "Load the full content of a skill's SKILL.md file."
                        " Call this when you need detailed instructions or"
                        " guidance from a specific skill."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "skill_name": {
                                "type": "string",
                                "description": (
                                    "The name of the skill to load"
                                    " (e.g., 'git-commit', 'code-review')"
                                ),
                            }
                        },
                        "required": ["skill_name"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "read_skill_resource",
                    "description": (
                        "Read a supplementary resource file from a"
                        " skill directory (e.g., templates, reference"
                        " docs, examples)."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "skill_name": {
                                "type": "string",
                                "description": "The name of the skill",
                            },
                            "resource_name": {
                                "type": "string",
                                "description": (
                                    "The filename of the resource to read"
                                    " (e.g., 'template.md', 'README.md',"
                                    " 'rules.txt')"
                                ),
                            },
                        },
                        "required": ["skill_name", "resource_name"],
                    },
                },
            },
        ]


# Global skills provider instance
_global_skills_provider: SkillsProvider | None = None


def get_skills_provider() -> SkillsProvider:
    """Get the global skills provider instance."""
    global _global_skills_provider
    if _global_skills_provider is None:
        _global_skills_provider = SkillsProvider()
    return _global_skills_provider


def load_skill(skill_name: str) -> str:
    """
    Tool function to load a skill's SKILL.md content.

    Args:
        skill_name: Name of the skill to load

    Returns:
        The full SKILL.md content, or error message if not found
    """
    report_start(f"🎓 Loading skill '{skill_name}'...", end="")

    provider = get_skills_provider()
    skill = provider.get_skill(skill_name)

    if skill is None:
        available = [s["name"] for s in provider.list_skills()]
        if available:
            error_msg = f"Skill '{skill_name}' not found. Available skills: {', '.join(available)}"
            report_error(error_msg)
            return error_msg
        error_msg = (
            f"Skill '{skill_name}' not found. No skills are currently installed."
        )
        report_error(error_msg)
        return error_msg

    content = skill.load_content()

    if not content:
        error_msg = f"Skill '{skill_name}' has no SKILL.md content."
        report_error(error_msg)
        return error_msg

    # Count lines for result message
    line_count = len(content.split("\n"))
    report_result(f"Loaded '{skill_name}' ({line_count} lines)")

    return f"# {skill_name}\n\n{content}"


def read_skill_resource(skill_name: str, resource_name: str) -> str:
    """
    Tool function to read a skill's resource file.

    Args:
        skill_name: Name of the skill
        resource_name: Filename of the resource to read

    Returns:
        The resource content, or error message if not found
    """
    report_start(
        f"📄 Reading resource '{resource_name}' from skill '{skill_name}'...", end=""
    )

    provider = get_skills_provider()
    skill = provider.get_skill(skill_name)

    if skill is None:
        available = [s["name"] for s in provider.list_skills()]
        if available:
            error_msg = f"Skill '{skill_name}' not found. Available skills: {', '.join(available)}"
            report_error(error_msg)
            return error_msg
        error_msg = (
            f"Skill '{skill_name}' not found. No skills are currently installed."
        )
        report_error(error_msg)
        return error_msg

    content = skill.get_resource(resource_name)

    if content is None:
        available = list(skill.resources.keys())
        if available:
            error_msg = (
                f"Resource '{resource_name}' not found in skill"
                f" '{skill_name}'. Available resources:"
                f" {', '.join(available)}"
            )
            report_error(error_msg)
            return error_msg
        error_msg = (
            f"Resource '{resource_name}' not found in skill"
            f" '{skill_name}'. This skill has no additional resources."
        )
        report_error(error_msg)
        return error_msg

    # Count lines for result message
    line_count = len(content.split("\n"))
    report_result(
        f"Read resource '{resource_name}' from '{skill_name}' ({line_count} lines)"
    )

    return f"# {skill_name}/{resource_name}\n\n{content}"


def get_skills_advertisement() -> str:
    """Get the skills advertisement for system prompt."""
    return get_skills_provider().get_advertisement()


def get_skills_tools() -> dict[str, Any]:
    """Get skill-related tools as a dict mapping names to functions."""
    return {
        "load_skill": load_skill,
        "read_skill_resource": read_skill_resource,
    }
