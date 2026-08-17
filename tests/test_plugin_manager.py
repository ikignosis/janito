"""Tests for the plugin framework (janito.plugin_manager).

Covers the ``--plugin`` / ``--list-plugins`` CLI flags, contract validation,
scoped ``sys.path`` handling, and registration of plugin tools, commands and
system-prompt sections.  Also exercises loading the real codesearch plugin
(``../plugins/janito-codesearch-plugin``) end-to-end.
"""

import sys
from pathlib import Path

import pytest

import janito.plugin_manager as plugin_manager
from janito.tooling.tools_registry import get_all_tool_schemas

REPO_ROOT = Path(__file__).resolve().parent.parent

# The real codesearch plugin, now maintained outside the repo as a sibling
# of the janito checkout (a sibling "plugins" collection).
CODESEARCH_PLUGIN_DIR = REPO_ROOT.parent / "plugins" / "janito-codesearch-plugin"

# Toy plugin source implementing the full contract.
TOY_PLUGIN_SRC = '''\
from janito.shell.cmds.base import CmdHandler
from janito.tooling import BaseTool
from janito.tooling.decorator import tool

name = "toyplugin"


def on_start():
    print("toy on_start ran")
    return None


SYSTEM_PROMPT = "You have access to the toy plugin."


@tool(permissions="r")
class ToyTool(BaseTool):
    """Toy plugin tool - answers with the query."""

    def run(self, query: str) -> dict:
        return {"success": True, "query": query, "plugin": "toy"}


class ToyCmd(CmdHandler):
    """Command handler for /toy."""

    @property
    def name(self):
        return "/toy"

    def handle(self, shell, user_input: str) -> bool:
        return user_input.lower().startswith("/toy")


TOOLS = [ToyTool]
CMD_HANDLERS = [ToyCmd]
'''


@pytest.fixture(autouse=True)
def _restore_global_state():
    """Isolate the module-level plugin state (prompt sections, registry,
    commands, loaded plugins) between tests."""
    import janito.system_prompt as system_prompt_mod
    from janito.shell.cmds import registry as cmds_registry
    from janito.tooling import tools_registry

    saved_sections = list(system_prompt_mod._PLUGIN_SECTIONS)
    saved_loaded = list(plugin_manager.LOADED_PLUGINS)
    saved_commands = list(cmds_registry._commands)
    saved_tools = set(tools_registry.AVAILABLE_TOOLS)

    system_prompt_mod._PLUGIN_SECTIONS = list(saved_sections)
    plugin_manager.LOADED_PLUGINS = list(saved_loaded)

    yield

    # Restore prompt sections, loaded-plugins list and command registry.
    system_prompt_mod._PLUGIN_SECTIONS = list(saved_sections)
    plugin_manager.LOADED_PLUGINS = list(saved_loaded)
    cmds_registry._commands = list(saved_commands)
    # Drop any tools a plugin registered (e.g. ToyTool / CodeSearch).
    for name in list(tools_registry.AVAILABLE_TOOLS):
        if name not in saved_tools:
            tools_registry.AVAILABLE_TOOLS.pop(name, None)


# Toy plugin with a failing on_start.
FAILING_PLUGIN_SRC = """\
name = "failing"


def on_start():
    return "index build failed"
"""

# Toy plugin missing required symbols.
INCOMPLETE_PLUGIN_SRC = """\
name = "incomplete"
"""


def _purge_module(name: str) -> None:
    """Remove a plugin package and its submodules from sys.modules."""
    for mod in list(sys.modules):
        if mod == name or mod.startswith(name + "."):
            del sys.modules[mod]


@pytest.fixture()
def toy_plugin(tmp_path):
    """Create a toy plugin package in a temp dir."""
    plugin_dir = tmp_path / "toyplugin"
    plugin_dir.mkdir()
    (plugin_dir / "__init__.py").write_text(TOY_PLUGIN_SRC, encoding="utf-8")
    _purge_module("toyplugin")
    yield plugin_dir
    _purge_module("toyplugin")


def _plugin_names(plugin_list):
    return [p.name for p in plugin_list]


# ---------------------------------------------------------------------------
# CLI flags
# ---------------------------------------------------------------------------


def test_parser_exposes_plugin_flags():
    from janito.cli.parser import create_parser

    args = create_parser().parse_args(
        [
            "--plugin",
            "../plugins/janito-codesearch-plugin",
            "--plugin",
            "plugins/other",
            "prompt",
        ]
    )
    assert args.plugin == [
        "../plugins/janito-codesearch-plugin",
        "plugins/other",
    ]

    args = create_parser().parse_args(["--list-plugins"])
    assert args.list_plugins is True


# ---------------------------------------------------------------------------
# Loading and contract validation
# ---------------------------------------------------------------------------


def test_load_plugin_registers_content(toy_plugin, monkeypatch):
    """A valid plugin registers its tool, command and system-prompt text."""
    from janito.shell.cmds import get_registered_commands
    from janito.system_prompt import get_system_prompt_with_skills

    monkeypatch.setattr(plugin_manager, "LOADED_PLUGINS", [])
    plugin = plugin_manager.load_plugin(toy_plugin)

    assert plugin.loaded
    assert plugin.name == "toyplugin"
    assert plugin.load_error is None

    # Tool registered in the tools registry.
    schemas = get_all_tool_schemas()
    names = {s["function"]["name"] for s in schemas}
    assert "ToyTool" in names

    # Command registered with the shell.
    command_names = [c.name for c in get_registered_commands()]
    assert "/toy" in command_names

    # System prompt text appended.
    assert "You have access to the toy plugin." in get_system_prompt_with_skills()


def test_load_plugin_prints_loading_message(toy_plugin, capsys):
    """load_plugin prints \"Loading plugin <name>\" before loading."""
    plugin_manager.load_plugin(toy_plugin)

    out = capsys.readouterr().out
    assert "Loading plugin toyplugin" in out


def test_load_plugin_restores_sys_path(toy_plugin):
    """sys.path is byte-identical before and after loading a plugin."""
    before = list(sys.path)
    plugin_manager.load_plugin(toy_plugin)
    assert sys.path == before


def test_load_plugin_captures_on_start_error(tmp_path):
    """A failing on_start records the error but does not raise."""
    plugin_dir = tmp_path / "failing"
    plugin_dir.mkdir()
    (plugin_dir / "__init__.py").write_text(FAILING_PLUGIN_SRC, encoding="utf-8")
    _purge_module("failing")

    plugin = plugin_manager.load_plugin(plugin_dir)

    assert not plugin.loaded
    assert plugin.load_error == "index build failed"


def test_load_plugin_missing_contract(tmp_path):
    """Missing required symbols produce a load error."""
    plugin_dir = tmp_path / "incomplete"
    plugin_dir.mkdir()
    (plugin_dir / "__init__.py").write_text(INCOMPLETE_PLUGIN_SRC, encoding="utf-8")
    _purge_module("incomplete")

    plugin = plugin_manager.load_plugin(plugin_dir)

    assert not plugin.loaded
    assert "missing required symbols" in plugin.load_error
    assert "on_start" in plugin.load_error


def test_load_plugin_missing_dir(tmp_path):
    """A nonexistent plugin dir records an import error."""
    plugin = plugin_manager.load_plugin(tmp_path / "does_not_exist")
    assert not plugin.loaded
    assert "failed to import" in plugin.load_error


# ---------------------------------------------------------------------------
# load_plugins() list API
# ---------------------------------------------------------------------------


def test_load_plugins_appends_to_loaded(toy_plugin, monkeypatch):
    monkeypatch.setattr(plugin_manager, "LOADED_PLUGINS", [])
    plugins = plugin_manager.load_plugins([str(toy_plugin)])

    assert [p.name for p in plugins] == ["toyplugin"]
    assert plugin_manager.LOADED_PLUGINS == plugins


def test_load_plugins_empty():
    assert plugin_manager.load_plugins(None) == []
    assert plugin_manager.load_plugins([]) == []


# ---------------------------------------------------------------------------
# Real codesearch plugin end-to-end
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not CODESEARCH_PLUGIN_DIR.is_dir(),
    reason="codesearch plugin not checked out at ../plugins/janito-codesearch-plugin",
)
def test_codesearch_plugin_loads_and_creates_index(tmp_path, monkeypatch):
    """Loading the codesearch plugin auto-creates .janito/codesearch.db."""
    from janito.shell.cmds import get_registered_commands

    (tmp_path / "hello.py").write_text(
        "def hello_world():\n    print('hello world')\n", encoding="utf-8"
    )
    monkeypatch.chdir(tmp_path)
    _purge_module("janito-codesearch-plugin")

    plugin = plugin_manager.load_plugin(CODESEARCH_PLUGIN_DIR)

    assert plugin.loaded, plugin.load_error
    assert plugin.name == "codesearch"

    # Index auto-created by on_start().
    assert (tmp_path / ".janito" / "codesearch.db").is_file()

    # Tool registered.
    schemas = get_all_tool_schemas()
    assert "CodeSearch" in {s["function"]["name"] for s in schemas}

    # /codesearch command registered.
    assert "/codesearch" in [c.name for c in get_registered_commands()]

    # System prompt section instructs to prefer CodeSearch for text search.
    from janito.system_prompt import (
        get_system_prompt_sections,
        get_system_prompt_with_skills,
    )

    prompt = get_system_prompt_with_skills()
    assert "## Plugin:" not in prompt
    assert (
        "When searching text on files use the CodeSearch tool before the "
        "other search tools" in prompt
    )

    # The plugin section keeps a leading newline so its text is separated
    # from the previous section by a blank line in the final prompt.
    plugin_sections = [
        (name, text)
        for name, text in get_system_prompt_sections()
        if name == "plugins:codesearch"
    ]
    assert len(plugin_sections) == 1
    _, plugin_text = plugin_sections[0]
    assert plugin_text.startswith("\n")
    assert (
        "When searching text on files use the CodeSearch tool before the "
        "other search tools" in plugin_text
    )

    _purge_module("janito-codesearch-plugin")
