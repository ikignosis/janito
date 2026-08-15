"""
Tests for SessionSetup (janito.cli.session_setup).

SessionSetup centralizes the system-prompt and toolset selection that was
previously duplicated between ``cli/chat.py`` and
``janito.web.backend.config.WebServerConfig``.  These tests verify the
resolution chain, the tools suppression rules, and that the CLI and web
entry points produce identical results for the same flags.
"""

import sys
from pathlib import Path

# Add the repo root to sys.path to allow importing the package directly.
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from janito.cli.session_setup import SessionSetup


def _args(**overrides):
    """Build a minimal argparse-like object with the session flags."""
    defaults = {
        "system_prompt": None,
        "no_system_prompt": False,
        "gmail": False,
        "onedrive": False,
    }
    defaults.update(overrides)
    return type("Args", (), defaults)()


if pytest is not None:
    # ---- resolution chain ----------------------------------------------

    def test_default_uses_skills_prompt():
        setup = SessionSetup()
        from janito.system_prompt import get_system_prompt_with_skills

        assert setup.effective_system_prompt() == get_system_prompt_with_skills()
        assert setup.no_tools is False

    def test_custom_system_prompt_wins():
        setup = SessionSetup(system_prompt="You are a cow")
        assert setup.effective_system_prompt() == "You are a cow"
        assert setup.no_tools is False

    def test_no_system_prompt_yields_none():
        setup = SessionSetup(no_system_prompt=True)
        assert setup.effective_system_prompt() is None
        assert setup.no_tools is True

    def test_onedrive_prompt():
        from janito.tools.onedrive import ONEDRIVE_SYSTEM_PROMPT

        setup = SessionSetup(onedrive=True)
        assert setup.effective_system_prompt() == ONEDRIVE_SYSTEM_PROMPT
        assert setup.no_tools is False

    def test_gmail_prompt():
        from janito.tools.gmail import GMAIL_SYSTEM_PROMPT

        setup = SessionSetup(gmail=True)
        assert setup.effective_system_prompt() == GMAIL_SYSTEM_PROMPT
        assert setup.no_tools is False

    def test_onedrive_wins_over_gmail():
        from janito.tools.onedrive import ONEDRIVE_SYSTEM_PROMPT

        setup = SessionSetup(gmail=True, onedrive=True)
        assert setup.effective_system_prompt() == ONEDRIVE_SYSTEM_PROMPT

    def test_custom_prompt_wins_over_modes():
        setup = SessionSetup(system_prompt="custom", gmail=True, onedrive=True)
        assert setup.effective_system_prompt() == "custom"

    # ---- single-prompt context -----------------------------------------

    def test_messages_and_tools_context():
        # Default: seeded system message, tools=None (use all).
        setup = SessionSetup()
        messages, tools = setup.messages_context(), setup.tools_arg()
        assert len(messages) == 1 and messages[0]["role"] == "system"
        assert tools is None

        # Custom prompt: seeded message, tools=None (use all).
        setup = SessionSetup(system_prompt="custom")
        assert setup.messages_context() == [{"role": "system", "content": "custom"}]
        assert setup.tools_arg() is None

        # No system prompt: no seed, tools=[].
        setup = SessionSetup(no_system_prompt=True)
        assert setup.messages_context() == []
        assert setup.tools_arg() == []

    # ---- toolset enablement --------------------------------------------

    def test_enable_toolsets_gmail_and_onedrive(monkeypatch):
        import janito.tooling.tools_registry as tools_registry

        added = []
        monkeypatch.setattr(
            tools_registry, "add_toolset", lambda name: added.append(name)
        )
        SessionSetup(gmail=True, onedrive=True).enable_toolsets(extra=["janitoweb"])
        assert added == ["janitoweb", "gmail", "onedrive"]

    def test_enable_toolsets_nothing_when_not_requested(monkeypatch):
        import janito.tooling.tools_registry as tools_registry

        added = []
        monkeypatch.setattr(
            tools_registry, "add_toolset", lambda name: added.append(name)
        )
        SessionSetup().enable_toolsets()
        assert added == []

    # ---- CLI <-> web parity --------------------------------------------

    def test_cli_and_web_resolve_identical_prompts():
        """The same flags produce the same prompt from cli/chat.py and WebServerConfig."""
        import janito.cli.chat as chat_mod
        from janito.web.backend.config import WebServerConfig

        for flags in (
            {},
            {"system_prompt": "custom"},
            {"no_system_prompt": True},
            {"gmail": True},
            {"onedrive": True},
            {"gmail": True, "onedrive": True},
        ):
            cli_prompt, _ = chat_mod._resolve_system_prompt(_args(**flags))
            config = WebServerConfig(
                system_prompt=flags.get("system_prompt"),
                no_system_prompt=flags.get("no_system_prompt", False),
                gmail=flags.get("gmail", False),
                onedrive=flags.get("onedrive", False),
            )
            assert config.get_effective_system_prompt() == cli_prompt

    def test_cli_and_web_enable_same_toolsets(monkeypatch):
        """cli/chat.py and WebServerConfig call add_toolset with the same names."""
        import janito.cli.chat as chat_mod
        import janito.tooling.tools_registry as tools_registry
        from janito.web.backend.config import WebServerConfig

        added = []
        monkeypatch.setattr(
            tools_registry, "add_toolset", lambda name: added.append(name)
        )

        chat_mod._enable_requested_toolsets(_args(gmail=True, onedrive=True))
        cli_added = list(added)
        added.clear()

        WebServerConfig(gmail=True, onedrive=True).apply_toolsets()
        web_added = list(added)

        # The web mode additionally loads the web-only toolset.
        assert cli_added == ["gmail", "onedrive"]
        assert web_added == ["janitoweb", "gmail", "onedrive"]

else:  # pragma: no cover - fallback runner without pytest

    def _main():
        class _MP:
            def __init__(self):
                self._undo = []

            def setattr(self, obj, name, value):
                self._undo.append((obj, name, getattr(obj, name)))
                setattr(obj, name, value)

            def restore(self):
                for obj, name, value in reversed(self._undo):
                    setattr(obj, name, value)

        for name, fn in sorted(globals().items()):
            if name.startswith("test_") and callable(fn):
                mp = _MP()
                try:
                    fn(mp)
                finally:
                    mp.restore()
                print(f"OK {name}")

    if __name__ == "__main__":
        _main()
