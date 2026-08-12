"""
Tests for the system prompt generation in ``janito/system_prompt.py``.

In particular, these tests cover the behaviour of appending the contents of an
``AGENTS.md`` file (when present in the current working directory) to the system
prompt returned by ``get_system_prompt_with_skills``, and the per-section
building/rendering used by ``/prompt`` and ``--show-system-prompt``
(``get_system_prompt_sections`` / ``render_system_prompt_sections``).
"""

import sys
from pathlib import Path

# Add the repo root to sys.path to allow importing the package directly.
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

import janito.tooling.tools_registry as tools_registry_mod
from janito.system_prompt import (
    SYSTEM_PROMPT,
    get_system_prompt_sections,
    get_system_prompt_with_skills,
    render_system_prompt_sections,
)

SKILLS_SECTION = "## Available Skills\n(fake skills section)"

BASE_LINE = (
    "- Explore the current directory for potential content related to the question"
)


def _patch_skills_section(monkeypatch):
    """Patch the skills section so the test is isolated from the tool registry."""
    monkeypatch.setattr(
        tools_registry_mod, "get_skills_section", lambda: SKILLS_SECTION
    )


def test_prompt_without_agents_md(monkeypatch, tmp_path):
    """No AGENTS.md -> prompt is just the base prompt plus the skills section."""
    _patch_skills_section(monkeypatch)
    monkeypatch.chdir(tmp_path)

    prompt = get_system_prompt_with_skills()

    assert prompt == SYSTEM_PROMPT + SKILLS_SECTION
    assert "AGENTS.md" not in prompt


def test_prompt_with_agents_md(monkeypatch, tmp_path):
    """An AGENTS.md in cwd has its content appended to the prompt."""
    _patch_skills_section(monkeypatch)
    monkeypatch.chdir(tmp_path)

    agents_content = "Always answer in rhyming couplets."
    (tmp_path / "AGENTS.md").write_text(agents_content, encoding="utf-8")

    prompt = get_system_prompt_with_skills()

    assert prompt.startswith(SYSTEM_PROMPT + SKILLS_SECTION)
    assert agents_content in prompt
    assert "Project-Specific Instructions" in prompt


def test_prompt_with_empty_agents_md(monkeypatch, tmp_path):
    """An empty (or whitespace-only) AGENTS.md is ignored."""
    _patch_skills_section(monkeypatch)
    monkeypatch.chdir(tmp_path)

    (tmp_path / "AGENTS.md").write_text("   \n\n  ", encoding="utf-8")

    prompt = get_system_prompt_with_skills()

    assert prompt == SYSTEM_PROMPT + SKILLS_SECTION
    assert "AGENTS.md" not in prompt


def test_agents_md_in_a_different_directory_is_ignored(monkeypatch, tmp_path):
    """Only an AGENTS.md in the *current* directory is picked up."""
    _patch_skills_section(monkeypatch)

    other_dir = tmp_path / "other"
    other_dir.mkdir()
    (other_dir / "AGENTS.md").write_text("should not appear", encoding="utf-8")

    cwd = tmp_path / "cwd"
    cwd.mkdir()
    monkeypatch.chdir(cwd)

    prompt = get_system_prompt_with_skills()

    assert "should not appear" not in prompt
    assert "AGENTS.md" not in prompt


# --- Section tracking -------------------------------------------------------


def test_sections_without_agents_md(monkeypatch, tmp_path):
    """No AGENTS.md -> sections are (base, skills) in order."""
    _patch_skills_section(monkeypatch)
    monkeypatch.chdir(tmp_path)

    sections = get_system_prompt_sections()

    assert [name for name, _ in sections] == ["base", "skills"]
    assert sections[0] == ("base", SYSTEM_PROMPT)
    assert sections[1] == ("skills", SKILLS_SECTION)


def test_sections_with_agents_md(monkeypatch, tmp_path):
    """An AGENTS.md in cwd adds an agents.md section after the skills one."""
    _patch_skills_section(monkeypatch)
    monkeypatch.chdir(tmp_path)

    agents_content = "Always answer in rhyming couplets."
    (tmp_path / "AGENTS.md").write_text(agents_content, encoding="utf-8")

    sections = get_system_prompt_sections()

    assert [name for name, _ in sections] == ["base", "skills", "agents.md"]
    assert sections[2][0] == "agents.md"
    assert agents_content in sections[2][1]


def test_sections_concatenation_reproduces_full_prompt(monkeypatch, tmp_path):
    """Joining the section texts yields the same prompt as the composed one."""
    _patch_skills_section(monkeypatch)
    monkeypatch.chdir(tmp_path)

    (tmp_path / "AGENTS.md").write_text("agent line", encoding="utf-8")

    sections = get_system_prompt_sections()
    joined = "".join(text for _, text in sections)

    assert joined == get_system_prompt_with_skills()


def test_render_system_prompt_sections_without_agents_md(monkeypatch, tmp_path):
    """Each section is prefixed with a ``---- <name> (<n> lines)`` header."""
    _patch_skills_section(monkeypatch)
    monkeypatch.chdir(tmp_path)

    rendered = render_system_prompt_sections(get_system_prompt_sections())
    lines = rendered.splitlines()

    assert lines[0] == "---- base (1 lines)"
    assert lines[1] == BASE_LINE
    assert lines[2] == "---- skills (2 lines)"
    assert lines[3:] == ["## Available Skills", "(fake skills section)"]


def test_render_system_prompt_sections_with_agents_md(monkeypatch, tmp_path):
    """The agents.md section header reports its displayed line count."""
    _patch_skills_section(monkeypatch)
    monkeypatch.chdir(tmp_path)

    agents_content = "line one\nline two"
    (tmp_path / "AGENTS.md").write_text(agents_content, encoding="utf-8")

    rendered = render_system_prompt_sections(get_system_prompt_sections())
    lines = rendered.splitlines()

    # agents.md section: "## Project-Specific..." header + blank + 2 content lines
    agents_idx = lines.index("---- agents.md (4 lines)")
    assert lines[agents_idx + 1] == "## Project-Specific Instructions"
    assert lines[agents_idx + 3 : agents_idx + 5] == ["line one", "line two"]


if __name__ == "__main__":  # pragma: no cover
    if pytest is not None:
        raise SystemExit(pytest.main([__file__, "-v"]))
