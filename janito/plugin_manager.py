"""Plugin loading framework.

A plugin is a directory with a Python package structure (e.g.
``../plugins/janito-codesearch-plugin/``).  Loading a plugin
**temporarily** adds the
plugin's **parent directory** to the front of ``sys.path`` so the package
can be imported by its directory name and **relative imports inside the
plugin code** resolve.  The package and the modules it imports are loaded
while the entry is active; afterwards ``sys.path`` is restored.

A plugin package must export the following symbols from its ``__init__.py``
(see ``docs/PLUGINS.md``):

- ``name`` — the plugin name (``str``).
- ``on_start`` — callable returning ``None`` on success or an error string.
- ``SYSTEM_PROMPT`` — ``str`` appended to the system prompt (default ``""``).
- ``TOOLS`` — list of tool classes (per ``docs/TOOL.md``) to register
  (default ``[]``).
- ``CMD_HANDLERS`` — list of ``CmdHandler`` subclasses to register with the
  shell (default ``[]``).
"""

from __future__ import annotations

import importlib
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .config_dir import get_config_dir
from .system_prompt import SECTION_PLUGINS, SYSTEM_PROMPT_MANAGER
from .tooling.tools_registry import register_plugin_tools
from .tools import discover_module_tools, wrap_tool_class

if TYPE_CHECKING:
    from types import ModuleType

# Plugins loaded by :func:`load_plugins` (used by ``janito --list-plugins``).
LOADED_PLUGINS: list[Plugin] = []

# Required contract symbols; the rest (SYSTEM_PROMPT/TOOLS/CMD_HANDLERS)
# default to empty values when absent.
REQUIRED_SYMBOLS = ("name", "on_start")


def get_default_plugins_dir() -> Path:
    """Get the default plugins directory (honors -c/--config-dir).

    Returns:
        Path: ``<config_dir>/plugins`` (default ``~/.janito/plugins``).
    """
    return get_config_dir() / "plugins"


@dataclass
class Plugin:
    """A loaded plugin and its contributed content.

    Attributes:
        name: The plugin name (from the plugin package).
        path: The plugin directory.
        module: The imported plugin package module (``None`` on load error).
        system_prompt: The plugin's ``SYSTEM_PROMPT`` text.
        tools: The tool classes contributed via ``TOOLS``.
        cmd_handlers: The ``CmdHandler`` classes contributed via
            ``CMD_HANDLERS``.
        load_error: ``None`` on success, otherwise a human-readable error
            string (missing contract symbols, ``on_start`` failure, ...).
    """

    name: str
    path: Path
    module: Any | None = None
    system_prompt: str = ""
    tools: list = field(default_factory=list)
    cmd_handlers: list = field(default_factory=list)
    load_error: str | None = None

    @property
    def loaded(self) -> bool:
        """Whether the plugin loaded without errors."""
        return self.load_error is None


@contextmanager
def _plugin_parent_on_sys_path(plugin_dir: Path) -> Iterator[None]:
    """Temporarily put the plugin's parent directory on ``sys.path``.

    The plugin directory itself is the package (it contains ``__init__.py``),
    so its **parent** must be on ``sys.path`` for it to import by directory
    name and for relative imports inside the package to resolve.  The entry
    is removed on exit; plugin modules loaded while the entry is active stay
    in ``sys.modules``.
    """
    parent = str(plugin_dir.resolve().parent)
    sys.path.insert(0, parent)
    try:
        yield
    finally:
        try:
            sys.path.remove(parent)
        except ValueError:
            pass


def _validate_plugin_module(plugin_dir: Path, module: ModuleType) -> str | None:
    """Validate the plugin contract; return an error string or ``None``."""
    missing = [sym for sym in REQUIRED_SYMBOLS if not hasattr(module, sym)]
    if missing:
        return (
            f"plugin at {plugin_dir} is missing required symbols: "
            f"{', '.join(missing)}"
        )
    if not callable(getattr(module, "on_start")):
        return f"plugin at {plugin_dir}: 'on_start' must be callable"
    if not isinstance(getattr(module, "name"), str):
        return f"plugin at {plugin_dir}: 'name' must be a string"
    return None


def _call_on_start(plugin: Plugin) -> None:
    """Run the plugin's ``on_start``; record an error string on failure."""
    assert plugin.module is not None
    try:
        error = plugin.module.on_start()
        if error:
            plugin.load_error = str(error)
    except Exception as e:  # noqa: BLE001 - a plugin must never crash startup
        plugin.load_error = f"on_start raised {type(e).__name__}: {e}"


def _register_plugin_tools(plugin: Plugin) -> None:
    """Register the plugin's tool classes into the tools registry."""
    wrapped: dict[str, Any] = {}
    for cls in plugin.tools:
        callable_tool = wrap_tool_class(cls)
        if callable_tool is not None:
            wrapped[callable_tool.__name__] = callable_tool
    # Fallback: if TOOLS is empty, discover tool classes from the plugin's
    # ``tools`` subpackage (the issue requires tools live under tools/).
    if not wrapped and plugin.module is not None:
        tools_submodule = getattr(plugin.module, "tools", None)
        if tools_submodule is not None:
            wrapped.update(discover_module_tools(tools_submodule))
    if wrapped:
        register_plugin_tools(wrapped)


def _register_plugin_commands(plugin: Plugin) -> None:
    """Register the plugin's ``CMD_HANDLERS`` with the interactive shell."""
    from .shell.cmds.registry import register_command

    for handler_cls in plugin.cmd_handlers:
        try:
            register_command(handler_cls())
        except Exception as e:  # noqa: BLE001 - never break startup
            if plugin.load_error is None:
                plugin.load_error = f"failed to register command: {e}"
            else:
                plugin.load_error += f"; failed to register command: {e}"


def _load_plugin_contents(plugin: Plugin, plugin_name: str) -> None:
    """Import a plugin package and register its tools, commands and prompt.

    Runs inside the parent-on-``sys.path`` context.  On success all of the
    plugin's content is registered; on failure (bad import, invalid contract,
    failing ``on_start``, ...) ``plugin.load_error`` is set and nothing is
    registered.
    """
    try:
        module = importlib.import_module(plugin_name)
    except Exception as e:  # noqa: BLE001 - never crash startup
        plugin.load_error = f"failed to import plugin {plugin_name}: {e}"
        return

    error = _validate_plugin_module(plugin.path, module)
    if error is not None:
        plugin.load_error = error
        return

    plugin.module = module
    plugin.name = getattr(module, "name", plugin_name)
    plugin.system_prompt = getattr(module, "SYSTEM_PROMPT", "") or ""
    plugin.tools = list(getattr(module, "TOOLS", []) or [])
    plugin.cmd_handlers = list(getattr(module, "CMD_HANDLERS", []) or [])

    _call_on_start(plugin)
    # A failed on_start (e.g. required secrets missing) means the plugin
    # does not load: none of its tools, commands or system-prompt text
    # are registered.
    if plugin.load_error is not None:
        return

    _register_plugin_tools(plugin)
    _register_plugin_commands(plugin)
    if plugin.system_prompt:
        section_name = f"{SECTION_PLUGINS}:{plugin.name}"
        try:
            SYSTEM_PROMPT_MANAGER.add_section(section_name, plugin.system_prompt)
        except ValueError:
            # A plugin with this name is already registered (e.g. the same
            # directory passed twice): replace its prompt text instead of
            # crashing on the duplicate section name.
            SYSTEM_PROMPT_MANAGER.update_section(section_name, plugin.system_prompt)


def load_plugin(plugin_dir: str | Path) -> Plugin:
    """Load a single plugin package from a directory.

    The plugin's parent directory is temporarily added to ``sys.path``, the
    package is imported, the contract is validated, ``on_start`` is called
    and the plugin's tools / commands / system-prompt sections are
    registered.  A failure never raises: it is recorded on the returned
    :class:`Plugin` as ``load_error``.  When ``on_start`` reports an error
    (e.g. required secrets are missing) the plugin **fails to load**: its
    tools, commands and system-prompt section are not registered.

    Args:
        plugin_dir: Path to the plugin directory (the package root).

    Returns:
        The loaded :class:`Plugin`.
    """
    plugin_path = Path(plugin_dir).resolve()
    plugin_name = plugin_path.name
    print(f"Loading plugin {plugin_name}", end="")
    plugin = Plugin(name=plugin_name, path=plugin_path)

    # Validate the directory before attempting the import, so a wrong
    # --plugin path produces a clear, actionable error instead of a
    # confusing "No module named ..." from importlib.
    if not plugin_path.is_dir():
        plugin.load_error = (
            f"plugin directory not found: {plugin_path} "
            "(check the path passed to --plugin)"
        )
    elif not (plugin_path / "__init__.py").is_file():
        plugin.load_error = (
            f"plugin directory has no __init__.py: {plugin_path} "
            "(a plugin must be a Python package)"
        )

    if plugin.load_error is None:
        with _plugin_parent_on_sys_path(plugin_path):
            _load_plugin_contents(plugin, plugin_name)

    if plugin.loaded:
        print(" OK")
    else:
        print(f" FAILED: {plugin.load_error}")
    return plugin


def load_plugins(plugin_dirs: list[str | Path] | None) -> list[Plugin]:
    """Load a list of plugin directories.

    Args:
        plugin_dirs: Plugin directories (from ``--plugin DIR``, repeatable).
            ``None`` or an empty list loads nothing.

    Returns:
        The list of loaded plugins (appended to :data:`LOADED_PLUGINS`).
    """
    if not plugin_dirs:
        return []
    plugins = [load_plugin(d) for d in plugin_dirs]
    LOADED_PLUGINS.extend(plugins)
    return plugins


def load_installed_plugins() -> list[Plugin]:
    """Autoload plugins from the default plugins directory.

    Scans ``~/.janito/plugins`` (honoring ``-c/--config-dir``) and loads
    every subdirectory that contains an ``__init__.py`` as a plugin.

    Returns:
        The list of autoloaded plugins (appended to :data:`LOADED_PLUGINS`).
    """
    plugins_dir = get_default_plugins_dir()
    if not plugins_dir.is_dir():
        return []

    plugins = []
    for entry in sorted(plugins_dir.iterdir()):
        if not entry.is_dir() or entry.name.startswith("."):
            continue
        if not (entry / "__init__.py").is_file():
            continue
        plugins.append(load_plugin(entry))

    LOADED_PLUGINS.extend(plugins)
    return plugins


def _read_plugin_name(plugin_dir: Path) -> str:
    """Return the plugin's ``name`` symbol without running its ``on_start``.

    The package is imported (module-level code runs, exactly as during a
    normal load) but ``on_start`` is NOT called and no tools, commands or
    system-prompt sections are registered.  Plugins that cannot be imported
    fall back to their directory name so a broken plugin can still be
    identified (and uninstalled) by directory name.

    Args:
        plugin_dir: The plugin package directory.

    Returns:
        The plugin's ``name`` (or the directory name as a fallback).
    """
    plugin_name = plugin_dir.name
    try:
        with _plugin_parent_on_sys_path(plugin_dir):
            module = importlib.import_module(plugin_name)
        value = getattr(module, "name", plugin_name)
        return value if isinstance(value, str) else plugin_name
    except Exception:  # noqa: BLE001 - never break the scan on a bad plugin
        return plugin_name


def scan_installed_plugins() -> list[tuple[str, Path]]:
    """Return ``(name, path)`` for every plugin installed in the plugins dir.

    Each installed plugin's actual ``name`` (the ``name`` symbol exported by
    its ``__init__.py``) is read without running its ``on_start`` hook, so
    scanning is side-effect free beyond the module import itself.  Plugins
    that cannot be imported fall back to their directory name.

    Returns:
        Sorted list of ``(name, path)`` pairs for the installed plugins
        (empty when the plugins dir does not exist or has no plugins).
    """
    plugins_dir = get_default_plugins_dir()
    if not plugins_dir.is_dir():
        return []

    results = []
    for entry in sorted(plugins_dir.iterdir()):
        if not entry.is_dir() or entry.name.startswith("."):
            continue
        if not (entry / "__init__.py").is_file():
            continue
        results.append((_read_plugin_name(entry), entry))
    return results
