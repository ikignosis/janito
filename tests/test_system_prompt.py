"""
Tests for the system prompt generation in ``janito/system_prompt.py``.

In particular, these tests cover the behaviour of appending the contents of an
``AGENTS.md`` file (when present in the current working directory) to the system
prompt returned by ``get_system_prompt_with_skills``.
"""

import sys
from pathlib import Path

# Add the repo root to sys.path to allow importing the package directly.
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

import janito.tooling.tools_registry as tools_registry_mod
from janito.system_prompt import SYSTEM_PROMPT, get_system_prompt_with_skills

SKILLS_SECTION = "## Available Skills\n(fake skills section)"


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
    assert "Project-Specific Instructions (from AGENTS.md)" in prompt


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


if __name__ == "__main__":  # pragma: no cover
    if pytest is not None:
        raise SystemExit(pytest.main([__file__, "-v"]))
