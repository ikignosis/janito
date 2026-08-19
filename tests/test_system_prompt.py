"""
Tests for the system prompt management in ``janito/system_prompt.py``.

The system prompt is assembled from named sections via
:class:`SysPromptManager`.  These tests cover the manager's section operations
(add/update/delete), rendering, and the default prompt built by
``sync_default_sections`` (base + skills + optional ``AGENTS.md``).
"""

import sys
from pathlib import Path

# Add the repo root to sys.path to allow importing the package directly.
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

import janito.tooling.tools_registry as tools_registry_mod
from janito.system_prompt import (
    SECTION_START,
    SYSTEM_PROMPT,
    SysPromptManager,
    sync_default_sections,
)

SKILLS_SECTION = "## Available Skills\n(fake skills section)"


def _patch_skills_section(monkeypatch):
    """Patch the skills section so the test is isolated from the tool registry."""
    monkeypatch.setattr(
        tools_registry_mod, "get_skills_section", lambda: SKILLS_SECTION
    )


# --- SysPromptManager unit tests -------------------------------------------


def test_init_seeds_start_section():
    """__init__ stores ('start', start_prompt) as the first section."""
    manager = SysPromptManager("start text")
    assert list(manager.get_all_sections()) == [(SECTION_START, "start text")]


def test_add_section_appends():
    """add_section appends the (name, text) pair after the start section."""
    manager = SysPromptManager("start text")
    manager.add_section("extra", "extra text")
    assert list(manager.get_all_sections()) == [
        (SECTION_START, "start text"),
        ("extra", "extra text"),
    ]


def test_add_section_duplicate_name_raises():
    """add_section raises ValueError when the name is already used."""
    manager = SysPromptManager("start text")
    manager.add_section("extra", "extra text")
    with pytest.raises(ValueError):
        manager.add_section("extra", "other text")


def test_add_section_duplicate_start_name_raises():
    """'start' is reserved; adding a second section named 'start' raises."""
    manager = SysPromptManager("start text")
    with pytest.raises(ValueError):
        manager.add_section(SECTION_START, "other start")


def test_update_section_replaces_text():
    """update_section replaces the text of an existing section."""
    manager = SysPromptManager("start text")
    manager.add_section("extra", "extra text")
    manager.update_section("extra", "updated text")
    assert list(manager.get_all_sections())[1] == ("extra", "updated text")


def test_update_section_missing_raises():
    """update_section raises ValueError for an unknown section."""
    manager = SysPromptManager("start text")
    with pytest.raises(ValueError):
        manager.update_section("missing", "text")


def test_del_section_removes():
    """del_section removes a non-start section."""
    manager = SysPromptManager("start text")
    manager.add_section("extra", "extra text")
    manager.del_section("extra")
    assert list(manager.get_all_sections()) == [(SECTION_START, "start text")]


def test_del_start_section_raises():
    """del_section raises ValueError when asked to delete 'start'."""
    manager = SysPromptManager("start text")
    with pytest.raises(ValueError):
        manager.del_section(SECTION_START)


def test_del_missing_section_raises():
    """del_section raises ValueError for an unknown section."""
    manager = SysPromptManager("start text")
    with pytest.raises(ValueError):
        manager.del_section("missing")


def test_render_appends_newline_after_each_section():
    """render joins sections with a trailing newline per section."""
    manager = SysPromptManager("first")
    manager.add_section("second", "second text")
    assert manager.render() == "first\nsecond text\n"


def test_render_without_sections_beyond_start():
    """A manager with only the start section renders start + newline."""
    manager = SysPromptManager("only start")
    assert manager.render() == "only start\n"


def test_get_all_sections_returns_iterator():
    """get_all_sections returns an iterator over (name, text) pairs."""
    manager = SysPromptManager("start text")
    iterator = manager.get_all_sections()
    assert iter(iterator) is iterator
    assert list(iterator) == [(SECTION_START, "start text")]


# --- default prompt building -----------------------------------------------


def test_system_prompt_content():
    """SYSTEM_PROMPT contains directory exploration instructions."""
    assert (
        "Explore the current directory for potential content related to the question"
    ) in SYSTEM_PROMPT
    assert not SYSTEM_PROMPT.startswith("\n")
    assert not SYSTEM_PROMPT.endswith("\n")


def test_prompt_without_agents_md(monkeypatch, tmp_path):
    """No AGENTS.md -> prompt is base + skills, one newline-separated section each."""
    _patch_skills_section(monkeypatch)
    monkeypatch.chdir(tmp_path)

    manager = SysPromptManager(SYSTEM_PROMPT)
    prompt = sync_default_sections(manager).render()

    assert prompt == SYSTEM_PROMPT + "\n" + SKILLS_SECTION + "\n"
    assert "AGENTS.md" not in prompt


def test_prompt_with_agents_md(monkeypatch, tmp_path):
    """An AGENTS.md in cwd appears as its own section in the prompt."""
    _patch_skills_section(monkeypatch)
    monkeypatch.chdir(tmp_path)

    agents_content = "Always answer in rhyming couplets."
    (tmp_path / "AGENTS.md").write_text(agents_content, encoding="utf-8")

    manager = SysPromptManager(SYSTEM_PROMPT)
    prompt = sync_default_sections(manager).render()

    assert prompt == (
        SYSTEM_PROMPT + "\n" + SKILLS_SECTION + "\n" + agents_content + "\n"
    )


def test_prompt_with_empty_agents_md(monkeypatch, tmp_path):
    """An empty (or whitespace-only) AGENTS.md is ignored."""
    _patch_skills_section(monkeypatch)
    monkeypatch.chdir(tmp_path)

    (tmp_path / "AGENTS.md").write_text("   \n\n  ", encoding="utf-8")

    manager = SysPromptManager(SYSTEM_PROMPT)
    prompt = sync_default_sections(manager).render()

    assert prompt == SYSTEM_PROMPT + "\n" + SKILLS_SECTION + "\n"
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

    manager = SysPromptManager(SYSTEM_PROMPT)
    prompt = sync_default_sections(manager).render()

    assert "should not appear" not in prompt
    assert "AGENTS.md" not in prompt


def test_sections_without_agents_md(monkeypatch, tmp_path):
    """No AGENTS.md -> sections are (start, skills) in order."""
    _patch_skills_section(monkeypatch)
    monkeypatch.chdir(tmp_path)

    manager = SysPromptManager(SYSTEM_PROMPT)
    sections = list(sync_default_sections(manager).get_all_sections())

    assert [name for name, _ in sections] == ["start", "skills"]
    assert sections[0] == ("start", SYSTEM_PROMPT)
    assert sections[1] == ("skills", SKILLS_SECTION)


def test_sections_with_agents_md(monkeypatch, tmp_path):
    """An AGENTS.md in cwd adds an agents.md section after the skills one."""
    _patch_skills_section(monkeypatch)
    monkeypatch.chdir(tmp_path)

    agents_content = "Always answer in rhyming couplets."
    (tmp_path / "AGENTS.md").write_text(agents_content, encoding="utf-8")

    manager = SysPromptManager(SYSTEM_PROMPT)
    sections = list(sync_default_sections(manager).get_all_sections())

    assert [name for name, _ in sections] == ["start", "skills", "agents.md"]
    assert sections[2][0] == "agents.md"
    assert agents_content in sections[2][1]


def test_sections_concatenation_reproduces_full_prompt(monkeypatch, tmp_path):
    """Rendering equals start text + newline + each section text + newline."""
    _patch_skills_section(monkeypatch)
    monkeypatch.chdir(tmp_path)

    agents_content = "agent line"
    (tmp_path / "AGENTS.md").write_text(agents_content, encoding="utf-8")

    manager = SysPromptManager(SYSTEM_PROMPT)
    sections = list(sync_default_sections(manager).get_all_sections())

    assert manager.render() == "".join(text + "\n" for _, text in sections)


def test_sync_removes_sections_that_no_longer_apply(monkeypatch, tmp_path):
    """When AGENTS.md disappears, the agents.md section is removed."""
    _patch_skills_section(monkeypatch)
    monkeypatch.chdir(tmp_path)

    manager = SysPromptManager(SYSTEM_PROMPT)
    (tmp_path / "AGENTS.md").write_text("agent line", encoding="utf-8")
    assert [name for name, _ in sync_default_sections(manager).get_all_sections()] == [
        "start",
        "skills",
        "agents.md",
    ]

    (tmp_path / "AGENTS.md").unlink()
    assert [name for name, _ in sync_default_sections(manager).get_all_sections()] == [
        "start",
        "skills",
    ]


if __name__ == "__main__":  # pragma: no cover
    if pytest is not None:
        raise SystemExit(pytest.main([__file__, "-v"]))
