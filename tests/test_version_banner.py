"""
Tests for the CLI version banner printed on the shell.

The banner is printed right before the "Running with full privileges" warning
and shows ``Janito x.y.z - Working at <cwd>`` with the version in cyan and the
working directory in magenta.
"""

import re
import sys
from pathlib import Path

# Add the repo root to sys.path to allow importing the package directly.
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from janito import __version__
from janito.cli.chat import print_version_banner

_ANSI = re.compile(r"\x1b\[[0-9;]*m")


def _strip_ansi(text):
    return _ANSI.sub("", text)


if pytest is not None:

    def test_version_banner_prints_version_and_cwd(monkeypatch, tmp_path, capsys):
        from rich.console import Console

        cwd = tmp_path
        monkeypatch.chdir(cwd)

        print_version_banner(Console(width=200))

        out = capsys.readouterr().out.strip()
        assert out == f"Janito {__version__} - Working at {cwd}"

    def test_version_banner_colors_version_cyan_and_cwd_magenta(monkeypatch, tmp_path):
        from rich.console import Console

        cwd = tmp_path
        monkeypatch.chdir(cwd)

        console = Console(force_terminal=True, width=200)
        with console.capture() as capture:
            print_version_banner(console)
        colored = capture.get()

        # The visible text still reads "Janito x.y.z - Working at <cwd>".
        assert (
            _strip_ansi(colored).strip() == f"Janito {__version__} - Working at {cwd}"
        )
        # Version is rendered in cyan, the working directory in magenta.
        assert "\x1b[36m" in colored
        assert "\x1b[35m" in colored

    def test_version_banner_maps_home_to_tilde(monkeypatch, tmp_path, capsys):
        """When the cwd is under the home dir, it is shown as ~/relative."""
        from rich.console import Console

        home = tmp_path / "home"
        project = home / "project"
        project.mkdir(parents=True)
        monkeypatch.setenv("HOME", str(home))
        monkeypatch.chdir(project)

        print_version_banner(Console(width=200))

        out = capsys.readouterr().out.strip()
        assert out == f"Janito {__version__} - Working at ~/project"

    def test_version_banner_maps_home_itself_to_tilde(monkeypatch, tmp_path, capsys):
        """When the cwd is the home dir itself, it is shown as ~."""
        from rich.console import Console

        home = tmp_path / "home"
        home.mkdir(parents=True)
        monkeypatch.setenv("HOME", str(home))
        monkeypatch.chdir(home)

        print_version_banner(Console(width=200))

        out = capsys.readouterr().out.strip()
        assert out == f"Janito {__version__} - Working at ~"

    def test_banner_precedes_full_privileges_warning(monkeypatch, capsys):
        """run_single_prompt prints the banner before the warning."""
        import janito.cli.chat as chat_mod

        # The banner must not have been printed yet in this test process
        # (other tests call print_version_banner directly).
        monkeypatch.setattr(chat_mod, "_banner_printed", False)

        class _Args:
            full_privileges = True
            gmail = False
            onedrive = False
            prompt = "hi"
            verbose = False
            thinking = False
            model = None
            provider = None
            reasoning_level = None
            system_prompt = None
            no_system_prompt = False

        monkeypatch.setattr(chat_mod, "send_prompt", lambda *a, **k: None)
        monkeypatch.setattr(chat_mod, "get_system_prompt_with_skills", lambda: "system")

        chat_mod.run_single_prompt(_Args())

        out = capsys.readouterr().out
        assert "Running with full privileges" in out
        assert out.index("Janito") < out.index("WARNING")

else:  # pragma: no cover - fallback runner without pytest

    def _main():
        for name, fn in sorted(globals().items()):
            if name.startswith("test_") and callable(fn):
                try:
                    fn()
                except TypeError:
                    # Skip tests that require monkeypatch/capsys fixtures.
                    continue
                print(f"OK {name}")

    if __name__ == "__main__":
        _main()
