"""
Tests for the /skills shell command.

The shell command lists all available skills (home + local) using the
skills provider. These tests verify the command is registered, dispatches
correctly, and renders the expected sections for populated and empty
skill sets.
"""

import sys
from pathlib import Path

# Add the repo root to sys.path to allow importing the package directly.
sys.path.insert(0, str(Path(__file__).parent.parent))

from unittest.mock import patch

import pytest

from janito.shell.cmds.skills import SkillsCmdHandler
from janito.tooling.skills_provider import SkillsProvider

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_skill(base: Path, name: str, description: str = "A test skill.") -> Path:
    """Create a minimal skill directory under *base* and return its path."""
    skill_dir = base / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: {description}\n---\n\n{description}\n",
        encoding="utf-8",
    )
    return skill_dir


def _provider_with(home_dir, local_dir=None) -> SkillsProvider:
    """Build a SkillsProvider from optional home/local directories."""
    paths = []
    if home_dir is not None:
        paths.append((home_dir, "home"))
    if local_dir is not None:
        paths.append((local_dir, "local"))
    return SkillsProvider(skill_paths=paths)


def _run_handler(provider, user_input="/skills"):
    """Run the /skills handler with a patched provider, capturing output."""
    import io

    from janito.tooling import skills_provider as sp

    handler = SkillsCmdHandler()
    output = io.StringIO()
    with patch("sys.stdout", output), patch.object(
        sp, "get_skills_provider", return_value=provider
    ):
        handled = handler.handle(object(), user_input)
    return handled, output.getvalue()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

if pytest is not None:

    def test_skills_command_is_registered():
        from janito.shell.cmds import get_registered_commands

        names = [c.name for c in get_registered_commands()]
        assert "/skills" in names

    def test_handler_name():
        assert SkillsCmdHandler().name == "/skills"

    def test_handle_dispatches_only_exact_command():
        handler = SkillsCmdHandler()
        assert handler.handle(object(), "/skills") is True
        assert handler.handle(object(), "/SKILLS") is True
        assert handler.handle(object(), "/skills extra") is False
        assert handler.handle(object(), "/tools") is False

    def test_lists_home_and_local_skills(tmp_path):
        home = tmp_path / "home" / "skills"
        local = tmp_path / "local" / "skills"
        home.mkdir(parents=True)
        local.mkdir(parents=True)
        _make_skill(home, "git-commit", "Commit with conventional commits")
        _make_skill(local, "code-review", "Review code for security issues")

        provider = _provider_with(home, local)
        handled, output = _run_handler(provider)

        assert handled is True
        assert "Home Skills" in output
        assert "Local Skills" in output
        assert "git-commit" in output
        assert "Commit with conventional commits" in output
        assert "code-review" in output
        assert "Review code for security issues" in output
        assert "2 skill(s) (1 home, 1 local)" in output

    def test_empty_output_shows_helpful_message(tmp_path):
        provider = _provider_with(tmp_path / "does_not_exist")
        handled, output = _run_handler(provider)

        assert handled is True
        assert "No skills installed." in output
        assert "--install-skill" in output

    def test_description_truncated(tmp_path):
        home = tmp_path / "home" / "skills"
        home.mkdir(parents=True)
        long_description = "x" * 200
        _make_skill(home, "long-skill", long_description)

        provider = _provider_with(home)
        _, output = _run_handler(provider)

        assert "x" * 60 not in output  # truncated, not the full 200 chars
        assert "..." in output

    def test_local_skill_shown_once_when_overriding(tmp_path):
        home = tmp_path / "home" / "skills"
        local = tmp_path / "local" / "skills"
        home.mkdir(parents=True)
        local.mkdir(parents=True)
        _make_skill(home, "shared", "Home version")
        _make_skill(local, "shared", "Local version")

        provider = _provider_with(home, local)
        _, output = _run_handler(provider)

        # The local copy wins, so only one entry appears.
        assert output.count("shared") == 1
        assert "Local version" in output
        assert "Home version" not in output

else:  # pragma: no cover - fallback runner without pytest

    def _main():
        import tempfile

        for name, fn in sorted(globals().items()):
            if name.startswith("test_") and callable(fn):
                with tempfile.TemporaryDirectory() as d:
                    fn(Path(d))
                print(f"OK {name}")

    if __name__ == "__main__":
        _main()
