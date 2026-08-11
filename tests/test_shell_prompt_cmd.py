"""
Tests for the ``/prompt`` shell command display.

``/prompt`` shows the effective system prompt; when it is the default
skills-advertising prompt, each section (``base``, ``skills``, ``agents.md``)
is displayed under a ``---- <name> (<n> lines)`` header so the user can see
how much of the prompt each source contributes and slice it.  Custom prompts
(``-S``) fall back to the plain full-text display.
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


def test_prompt_cmd_shows_section_headers(monkeypatch, tmp_path, capfd):
    """The default prompt is displayed section by section with line counts."""
    from janito.system_prompt import get_system_prompt_with_skills

    _patch_skills_section(monkeypatch)
    monkeypatch.chdir(tmp_path)

    shell = InteractiveShell(model="test-model", no_history=True)
    shell.initialize_history(system_prompt=get_system_prompt_with_skills())

    handler = PromptCmdHandler()
    assert handler.handle(shell, "/prompt") is True

    out = capfd.readouterr().out
    assert "System Prompt - Default (with Skills)" in out
    assert "---- base (1 lines)" in out
    assert "---- skills (2 lines)" in out


def test_prompt_cmd_includes_agents_md_section(monkeypatch, tmp_path, capfd):
    """An AGENTS.md in cwd appears as its own section with a line count."""
    from janito.system_prompt import get_system_prompt_with_skills

    _patch_skills_section(monkeypatch)
    monkeypatch.chdir(tmp_path)
    (tmp_path / "AGENTS.md").write_text("agent line", encoding="utf-8")

    shell = InteractiveShell(model="test-model", no_history=True)
    shell.initialize_history(system_prompt=get_system_prompt_with_skills())

    handler = PromptCmdHandler()
    assert handler.handle(shell, "/prompt") is True

    out = capfd.readouterr().out
    assert "---- agents.md (3 lines)" in out
    assert "agent line" in out


def test_prompt_cmd_custom_prompt_falls_back_to_plain(monkeypatch, tmp_path, capfd):
    """A custom (-S) prompt is shown in full without section headers."""
    _patch_skills_section(monkeypatch)
    monkeypatch.chdir(tmp_path)

    shell = InteractiveShell(model="test-model", no_history=True)
    shell.initialize_history(system_prompt="custom system prompt")

    handler = PromptCmdHandler()
    assert handler.handle(shell, "/prompt") is True

    out = capfd.readouterr().out
    assert "---- base" not in out
    assert "custom system prompt" in out


if __name__ == "__main__":  # pragma: no cover
    if pytest is not None:
        raise SystemExit(pytest.main([__file__, "-v"]))
