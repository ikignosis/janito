"""
Tests for the skills provider, focusing on home + local skill discovery.

Skills can be discovered from two locations:

* **Home**  – ``<config_dir>/skills``  (global, user-installed skills)
* **Local** – ``.janito/skills`` in the current working directory

Local skills with the same name as a home skill should take precedence.
Each skill must track its own filesystem path so that resources are loaded
from the correct directory.
"""

import sys
from pathlib import Path

# Add the repo root to sys.path to allow importing the package directly.
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

import janito.config_dir as config_dir_mod
from janito.tooling.skills_provider import SkillsProvider, get_local_skills_dir

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


def _make_resource(skill_dir: Path, filename: str, content: str = "resource content"):
    """Create a resource file inside a skill directory."""
    (skill_dir / filename).write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

if pytest is not None:

    def test_get_local_skills_dir_uses_cwd(monkeypatch, tmp_path):
        """``get_local_skills_dir`` resolves relative to the CWD."""
        monkeypatch.chdir(tmp_path)
        result = get_local_skills_dir()
        assert result == tmp_path / ".janito" / "skills"

    # ------------------------------------------------------------------
    # Home-only discovery (backward compatibility)
    # ------------------------------------------------------------------

    def test_home_skills_discovered(monkeypatch, tmp_path):
        home = tmp_path / "home" / "skills"
        home.mkdir(parents=True)
        _make_skill(home, "my-skill")

        provider = SkillsProvider(skill_paths=[(home, "home")])
        skills = provider.list_skills()
        assert len(skills) == 1
        assert skills[0]["name"] == "my-skill"
        assert skills[0]["source"] == "home"
        assert skills[0]["path"] == str(home / "my-skill")

    # ------------------------------------------------------------------
    # Local-only discovery
    # ------------------------------------------------------------------

    def test_local_skills_discovered(monkeypatch, tmp_path):
        local = tmp_path / "local" / "skills"
        local.mkdir(parents=True)
        _make_skill(local, "local-skill")

        provider = SkillsProvider(skill_paths=[(local, "local")])
        skills = provider.list_skills()
        assert len(skills) == 1
        assert skills[0]["name"] == "local-skill"
        assert skills[0]["source"] == "local"

    # ------------------------------------------------------------------
    # Local overrides home
    # ------------------------------------------------------------------

    def test_local_overrides_home(monkeypatch, tmp_path):
        home = tmp_path / "home" / "skills"
        local = tmp_path / "local" / "skills"
        home.mkdir(parents=True)
        local.mkdir(parents=True)

        # Same skill name in both
        home_dir = _make_skill(home, "shared", "Home version")
        local_dir = _make_skill(local, "shared", "Local version")

        provider = SkillsProvider(skill_paths=[(home, "home"), (local, "local")])
        skill = provider.get_skill("shared")
        assert skill is not None
        # Local should win
        assert skill.path == local_dir
        assert skill.path != home_dir
        assert skill.source == "local"

    # ------------------------------------------------------------------
    # Different skills in home and local
    # ------------------------------------------------------------------

    def test_home_and_local_different_skills(monkeypatch, tmp_path):
        home = tmp_path / "home" / "skills"
        local = tmp_path / "local" / "skills"
        home.mkdir(parents=True)
        local.mkdir(parents=True)

        _make_skill(home, "home-only")
        _make_skill(local, "local-only")

        provider = SkillsProvider(skill_paths=[(home, "home"), (local, "local")])
        names = {s["name"] for s in provider.list_skills()}
        assert names == {"home-only", "local-only"}

    # ------------------------------------------------------------------
    # Resources loaded from correct path
    # ------------------------------------------------------------------

    def test_resource_loaded_from_correct_path(monkeypatch, tmp_path):
        home = tmp_path / "home" / "skills"
        local = tmp_path / "local" / "skills"
        home.mkdir(parents=True)
        local.mkdir(parents=True)

        home_dir = _make_skill(home, "shared", "Home version")
        _make_resource(home_dir, "template.md", "HOME TEMPLATE")

        local_dir = _make_skill(local, "shared", "Local version")
        _make_resource(local_dir, "template.md", "LOCAL TEMPLATE")

        provider = SkillsProvider(skill_paths=[(home, "home"), (local, "local")])
        skill = provider.get_skill("shared")

        # Resource must come from the local (overriding) skill
        content = skill.get_resource("template.md")
        assert content is not None
        assert "LOCAL TEMPLATE" in content

    def test_resource_only_in_home(monkeypatch, tmp_path):
        home = tmp_path / "home" / "skills"
        home.mkdir(parents=True)
        home_dir = _make_skill(home, "home-skill", "Home version")
        _make_resource(home_dir, "ref.md", "HOME REF")

        provider = SkillsProvider(skill_paths=[(home, "home")])
        skill = provider.get_skill("home-skill")
        content = skill.get_resource("ref.md")
        assert content is not None
        assert "HOME REF" in content

    # ------------------------------------------------------------------
    # list_skills includes path and source
    # ------------------------------------------------------------------

    def test_list_skills_includes_path_and_source(monkeypatch, tmp_path):
        home = tmp_path / "home" / "skills"
        local = tmp_path / "local" / "skills"
        home.mkdir(parents=True)
        local.mkdir(parents=True)

        _make_skill(home, "skill-a")
        _make_skill(local, "skill-b")

        provider = SkillsProvider(skill_paths=[(home, "home"), (local, "local")])
        skills = {s["name"]: s for s in provider.list_skills()}

        assert "path" in skills["skill-a"]
        assert "source" in skills["skill-a"]
        assert skills["skill-a"]["source"] == "home"
        assert skills["skill-b"]["source"] == "local"

    # ------------------------------------------------------------------
    # Default skill_paths includes both home and local
    # ------------------------------------------------------------------

    def test_default_skill_paths_includes_home_and_local(monkeypatch, tmp_path):
        """When skill_paths is None, both home and local dirs are searched."""
        home = tmp_path / "fake_home" / ".janito" / "skills"
        local = tmp_path / "project" / ".janito" / "skills"
        home.mkdir(parents=True)
        local.mkdir(parents=True)

        _make_skill(home, "global-skill")
        _make_skill(local, "project-skill")

        # Point config_dir to our fake home
        monkeypatch.setattr(
            config_dir_mod, "_config_dir", tmp_path / "fake_home" / ".janito"
        )
        # Point CWD to our fake project
        monkeypatch.chdir(tmp_path / "project")

        provider = SkillsProvider()
        names = {s["name"] for s in provider.list_skills()}
        assert "global-skill" in names
        assert "project-skill" in names

    # ------------------------------------------------------------------
    # Empty / nonexistent directories
    # ------------------------------------------------------------------

    def test_nonexistent_dirs_handled_gracefully(monkeypatch, tmp_path):
        nonexistent = tmp_path / "does_not_exist" / "skills"
        provider = SkillsProvider(skill_paths=[(nonexistent, "home")])
        assert provider.list_skills() == []

    # ------------------------------------------------------------------
    # Two-level deep discovery still works
    # ------------------------------------------------------------------

    def test_two_level_deep_discovery(monkeypatch, tmp_path):
        base = tmp_path / "skills"
        base.mkdir(parents=True)
        # Skill nested one extra level: base/category/skill/SKILL.md
        _make_skill(base / "category", "nested-skill")

        provider = SkillsProvider(skill_paths=[(base, "home")])
        names = {s["name"] for s in provider.list_skills()}
        assert "nested-skill" in names

    # ------------------------------------------------------------------
    # Backward compatibility: bare Path entries (no tuple) default to "home"
    # ------------------------------------------------------------------

    def test_bare_path_defaults_to_home_source(monkeypatch, tmp_path):
        """Passing a bare Path (no source tuple) should still work and
        default the source to 'home'."""
        home = tmp_path / "home" / "skills"
        home.mkdir(parents=True)
        _make_skill(home, "legacy-skill")

        provider = SkillsProvider(skill_paths=[home])
        skills = provider.list_skills()
        assert len(skills) == 1
        assert skills[0]["source"] == "home"

else:  # pragma: no cover - fallback runner without pytest

    def _main():
        import tempfile

        class _MP:
            def __init__(self):
                self._chdir = None

            def chdir(self, path):
                import os

                os.chdir(path)

            def setattr(self, obj, name, value):
                setattr(obj, name, value)

        for name, fn in sorted(globals().items()):
            if name.startswith("test_") and callable(fn):
                with tempfile.TemporaryDirectory() as d:
                    fn(_MP(), Path(d))
                print(f"OK {name}")

    if __name__ == "__main__":
        _main()
