"""System prompt assembly.

The system prompt is an ordered list of named ``(section_name, section_text)``
pairs owned by a :class:`SysPromptManager`.  The shared manager
(:data:`SYSTEM_PROMPT_MANAGER`) is seeded with the ``start`` section holding
the built-in base prompt; :func:`sync_default_sections` keeps the ``skills``
and ``agents.md`` sections in sync with the tool registry and the cwd
``AGENTS.md``; plugins register ``plugins:<name>`` sections at load time (see
``janito.plugin_manager``).

Every consumer (``janito.cli.session_setup.SessionSetup``, the shell ``/prompt``
command, ``--show-system-prompt`` and the web backend) manipulates the prompt
through this shared manager so the sections stay consistent.
"""

from __future__ import annotations

import os
from collections.abc import Iterator

# The built-in base prompt used to seed the ``start`` section.  Kept without
# leading/trailing newlines: :meth:`SysPromptManager.render` appends a newline
# at the end of every section for visual separation.
SYSTEM_PROMPT = (
    "Explore the current directory for potential content related to the question"
)

# Section names used when building the default prompt.
SECTION_START = "start"
SECTION_SKILLS = "skills"
SECTION_AGENTS_MD = "agents.md"
SECTION_PLUGINS = "plugins"


class SysPromptManager:
    """Manage the system prompt as an ordered list of named sections.

    A section is a ``(section_name, section_text)`` pair.  The ``start``
    section is created in :meth:`__init__`, always stays first and cannot be
    deleted; every other section name must be unique.
    """

    def __init__(self, start_prompt: str) -> None:
        self._sections: list[tuple[str, str]] = [(SECTION_START, start_prompt)]

    def add_section(self, name: str, prompt: str) -> None:
        """Append a new section.

        Args:
            name: Unique section name.
            prompt: Section text.

        Raises:
            ValueError: if a section named ``name`` already exists.
        """
        if self._find(name) is not None:
            raise ValueError(f"a section named {name!r} already exists")
        self._sections.append((name, prompt))

    def update_section(self, name: str, prompt: str) -> None:
        """Replace the text of an existing section.

        Args:
            name: Section name.
            prompt: New section text.

        Raises:
            ValueError: if no section named ``name`` exists.
        """
        index = self._find(name)
        if index is None:
            raise ValueError(f"no section named {name!r} to update")
        self._sections[index] = (name, prompt)

    def del_section(self, name: str) -> None:
        """Remove a section.

        Args:
            name: Section name.

        Raises:
            ValueError: if ``name`` is the ``start`` section or no section
                named ``name`` exists.
        """
        if name == SECTION_START:
            raise ValueError("the 'start' section cannot be deleted")
        index = self._find(name)
        if index is None:
            raise ValueError(f"no section named {name!r} to delete")
        del self._sections[index]

    def render(self) -> str:
        """Assemble the full prompt from all sections.

        A newline is appended at the end of every section to provide a visual
        context separation between sections.
        """
        return "".join(text + "\n" for _, text in self._sections)

    def get_all_sections(self) -> Iterator[tuple[str, str]]:
        """Yield ``(section_name, section_text)`` for every section."""
        return iter(self._sections)

    def _find(self, name: str) -> int | None:
        """Return the index of the section named ``name``, or ``None``."""
        for index, (existing, _) in enumerate(self._sections):
            if existing == name:
                return index
        return None


# The shared manager used across the app (CLI, shell and web).
SYSTEM_PROMPT_MANAGER = SysPromptManager(SYSTEM_PROMPT)


def _load_agents_md() -> str | None:
    """Read the cwd ``AGENTS.md``, returning its stripped content.

    Returns ``None`` when the file is missing, unreadable or empty
    (whitespace-only).
    """
    agents_md_path = os.path.join(os.getcwd(), "AGENTS.md")
    if os.path.isfile(agents_md_path):
        try:
            with open(agents_md_path, encoding="utf-8") as f:
                agents_content = f.read().strip()
            if agents_content:
                return agents_content
        except OSError:
            pass
    return None


def _set_section(manager: SysPromptManager, name: str, text: str | None) -> None:
    """Set ``name`` on ``manager`` to ``text``; ``None``/empty removes it."""
    if manager._find(name) is not None:
        if text:
            manager.update_section(name, text)
        else:
            manager.del_section(name)
    elif text:
        manager.add_section(name, text)


def sync_default_sections(
    manager: SysPromptManager | None = None,
) -> SysPromptManager:
    """Sync the ``skills`` and ``agents.md`` sections and return the manager.

    The ``skills`` section mirrors the current tool registry advertisement and
    the ``agents.md`` section mirrors the cwd ``AGENTS.md``; sections that no
    longer apply are removed.  Uses the shared :data:`SYSTEM_PROMPT_MANAGER`
    when ``manager`` is ``None``.  Plugin sections are never touched here;
    they are registered at load time by ``janito.plugin_manager``.
    """
    from .tooling.tools_registry import get_skills_section

    target = manager if manager is not None else SYSTEM_PROMPT_MANAGER

    _set_section(target, SECTION_SKILLS, get_skills_section())
    _set_section(target, SECTION_AGENTS_MD, _load_agents_md())

    return target
