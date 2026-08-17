"""
Tests for the ``/prompt`` shell command display.

``/prompt`` shows the effective system prompt; when it is the default
skills-advertising prompt, each section (``base``, ``skills``, ``agents.md``)
is displayed as a row of a rich table so the user can see how much of the
prompt each source contributes.  Custom prompts (``-S``) fall back to a
plain single-column table with the full text.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

import janito.tooling.tools_registry as tools_registry_mod
from janito.shell import InteractiveShell
from janito.shell.cmds.prompt import PromptCmdHandler

SKILLS_SECTION = "## Available Skills\n(fake skills section)"


def _patch_skills_section(monkeypatch):
    """Patch the skills section so the test is isolated from the tool registry."""
    monkeypatch.setattr(
        tools_registry_mod, "get_skills_section", lambda: SKILLS_SECTION
    )


def test_prompt_cmd_shows_section_table(monkeypatch, tmp_path, capfd):
    """The default prompt is displayed as a rich table with per-section rows."""
    from janito.system_prompt import get_system_prompt_with_skills

    _patch_skills_section(monkeypatch)
    monkeypatch.chdir(tmp_path)

    shell = InteractiveShell(model="test-model", no_history=True)
    shell.initialize_history(system_prompt=get_system_prompt_with_skills())

    handler = PromptCmdHandler()
    assert handler.handle(shell, "/prompt") is True

    out = capfd.readouterr().out
    assert "System Prompt - Default (with Skills)" in out
    assert "base" in out
    assert "skills" in out
    assert "Available Skills" in out
    assert "(fake skills section)" in out
    # No more plain-text ==== / ---- headers.
    assert "----" not in out


def test_prompt_cmd_includes_agents_md_section(monkeypatch, tmp_path, capfd):
    """An AGENTS.md in cwd appears as its own row in the table."""
    from janito.system_prompt import get_system_prompt_with_skills

    _patch_skills_section(monkeypatch)
    monkeypatch.chdir(tmp_path)
    (tmp_path / "AGENTS.md").write_text("agent line", encoding="utf-8")

    shell = InteractiveShell(model="test-model", no_history=True)
    shell.initialize_history(system_prompt=get_system_prompt_with_skills())

    handler = PromptCmdHandler()
    assert handler.handle(shell, "/prompt") is True

    out = capfd.readouterr().out
    assert "agents.md" in out
    assert "agent line" in out


def test_prompt_cmd_custom_prompt_falls_back_to_plain(monkeypatch, tmp_path, capfd):
    """A custom (-S) prompt is shown in full inside a single-column table."""
    _patch_skills_section(monkeypatch)
    monkeypatch.chdir(tmp_path)

    shell = InteractiveShell(model="test-model", no_history=True)
    shell.initialize_history(system_prompt="custom system prompt")

    handler = PromptCmdHandler()
    assert handler.handle(shell, "/prompt") is True

    out = capfd.readouterr().out
    assert "System Prompt - Default" in out
    assert "custom system prompt" in out
    assert "----" not in out


def test_prompt_cmd_preserves_leading_whitespace_of_sections(
    monkeypatch, tmp_path, capfd
):
    """Leading whitespace of a section is kept in the table display.

    The base section starts with a newline and plugin sections are prefixed
    with one; ``rstrip`` (not ``strip``) keeps that leading whitespace so the
    rendered rows show the blank-line separation between sections.
    """
    from janito import system_prompt as system_prompt_mod
    from janito.system_prompt import get_system_prompt_with_skills

    _patch_skills_section(monkeypatch)
    monkeypatch.chdir(tmp_path)

    # Register a fake plugin section with a leading newline (as the plugin
    # loader does) and restore state afterwards.
    system_prompt_mod._PLUGIN_SECTIONS.append(("testplugin", "\nplugin section text"))
    try:
        shell = InteractiveShell(model="test-model", no_history=True)
        shell.initialize_history(system_prompt=get_system_prompt_with_skills())

        handler = PromptCmdHandler()
        assert handler.handle(shell, "/prompt") is True

        out = capfd.readouterr().out
        assert "plugins:testplugin" in out
        assert "plugin section text" in out
        # The leading newline of the plugin section shows as a blank content
        # row between the previous section and the plugin text.
        assert "\u2502\n\u2502 plugins:testplugin" in out
    finally:
        system_prompt_mod._PLUGIN_SECTIONS.pop()


if __name__ == "__main__":  # pragma: no cover
    if pytest is not None:
        raise SystemExit(pytest.main([__file__, "-v"]))
