import os

SYSTEM_PROMPT = """
- Explore the current directory for potential content related to the question
"""

# Section names used by :func:`get_system_prompt_sections`
SECTION_BASE = "base"
SECTION_SKILLS = "skills"
SECTION_AGENTS_MD = "agents.md"


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
    - ``agents.md`` — the cwd ``AGENTS.md`` content (only when present).

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
                "\n\n## Project-Specific Instructions\n\n" + agents_content + "\n",
            )
        )

    return sections


def get_system_prompt_with_skills() -> str:
    """Get the base system prompt with skills advertisement appended."""
    return "".join(text for _, text in get_system_prompt_sections())
