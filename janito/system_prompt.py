import os

SYSTEM_PROMPT = """
- Explore the current directory for potential content related to the question
"""

# Section names used by :func:`get_system_prompt_sections`
SECTION_BASE = "base"
SECTION_SKILLS = "skills"
SECTION_AGENTS_MD = "agents.md"
SECTION_PLUGINS = "plugins"

# Plugin-provided prompt sections ``(plugin_name, text)`` registered at load
# time by ``janito.plugin_manager``.  Appended after the AGENTS.md section
# (when plugins are loaded).
_PLUGIN_SECTIONS: list[tuple[str, str]] = []


def register_plugin_system_prompt(name: str, text: str) -> None:
    """Register a plugin's ``SYSTEM_PROMPT`` text to append to the prompt.

    Args:
        name: The plugin name (used as the section label).
        text: The prompt text contributed by the plugin.
    """
    if text:
        _PLUGIN_SECTIONS.append((name, text))


def _load_agents_md() -> str | None:
    """Read the cwd ``AGENTS.md``, returning its stripped content.

    Returns ``None`` when the file is missing, unreadable, or empty
    (whitespace-only).  Kept as a module-level helper so the section builder
    stays testable without filesystem side effects.
    """
    agents_md_path = os.path.join(os.getcwd(), "AGENTS.md")
    if os.path.isfile(agents_md_path):
        try:
            with open(agents_md_path, encoding="utf-8") as f:
                agents_content = f.read().strip()
            if agents_content:
                return agents_content
        except OSError:
            pass  # If the file can't be read, just skip it
    return None


def get_system_prompt_sections() -> list[tuple[str, str]]:
    """Build the default system prompt as an ordered list of ``(name, text)``.

    Each section stores the raw text **exactly as it appears in the final
    prompt** (separators included), so concatenating the texts reproduces
    :func:`get_system_prompt_with_skills` byte for byte.  The order is:

    - ``base`` — the built-in base prompt;
    - ``skills`` — the skills advertisement (only when non-empty);
    - ``agents.md`` — the cwd ``AGENTS.md`` content (only when present);
    - ``plugins`` — each loaded plugin's ``SYSTEM_PROMPT`` (only when plugins
      contribute prompt text).

    Consumers can slice the prompt per section using these boundaries; the
    shell ``/prompt`` command and ``janito --show-system-prompt`` display each
    section as a row of a rich table (Section, Lines, Content).
    """
    from .tooling.tools_registry import get_skills_section

    sections: list[tuple[str, str]] = [(SECTION_BASE, SYSTEM_PROMPT)]

    skills_section = get_skills_section()
    if skills_section:
        sections.append((SECTION_SKILLS, skills_section))

    agents_content = _load_agents_md()
    if agents_content is not None:
        sections.append(
            (
                SECTION_AGENTS_MD,
                "\n" + agents_content + "\n",
            )
        )

    for plugin_name, plugin_text in _PLUGIN_SECTIONS:
        sections.append((f"{SECTION_PLUGINS}:{plugin_name}", "\n" + plugin_text))

    return sections


def get_system_prompt_with_skills() -> str:
    """Get the base system prompt with skills advertisement appended."""
    return "".join(text for _, text in get_system_prompt_sections())
