# PLUGINS.md — Janito Plugin System

This document defines the plugin contract for **janito** and explains how to
write, load, and test a plugin.  Plugins let third-party code extend janito
with new tools, shell commands, and system-prompt content without modifying
the core package.

---

## Table of Contents

1. [What is a Plugin?](#what-is-a-plugin)
2. [The Plugin Contract](#the-plugin-contract)
3. [How Loading Works (sys.path)](#how-loading-works-syspath)
4. [Directory Layout](#directory-layout)
5. [Step-by-Step: A Minimal Plugin](#step-by-step-a-minimal-plugin)
6. [Loading Plugins](#loading-plugins)
7. [Installing Plugins](#installing-plugins)
8. [Available Plugins](#available-plugins)
9. [The codesearch Plugin (reference implementation)](#the-codesearch-plugin-reference-implementation)
10. [Interacting with janito](#interacting-with-janito)
11. [Checklist Before Submitting](#checklist-before-submitting)

---

## What is a Plugin?

A plugin is a **directory with a Python package structure** (a directory
containing an `__init__.py`), for example
`../plugins/janito-codesearch-plugin/`.  When
loaded, the plugin can contribute:

- **`TOOLS`** — tool classes (per `docs/TOOL.md`) that are added to the
  tools offered to the model alongside the built-in tools.
- **`CMD_HANDLERS`** — `CmdHandler` subclasses that provide new slash
  commands to the interactive shell.
- **`SYSTEM_PROMPT`** — text appended to the default system prompt.
- **`on_start()`** — a hook run when the plugin loads, typically used for
  one-time initialization (e.g. building an index).

The plugin package may contain other modules/packages as required (the
engine code, `tools/`, `cmd/`, tests, ...).

---

## The Plugin Contract

A plugin package **must** export the following symbols from its
`__init__.py`:

| Symbol | Type | Description |
|---|---|---|
| `name` | `str` | The plugin name. |
| `on_start` | `Callable[[], str \| None]` | Called when the plugin loads. Returns `None` on success, or a string describing the error. |
| `SYSTEM_PROMPT` | `str` | Text appended to the system prompt (may be `""`). |
| `TOOLS` | `list[type]` | Tool classes to register (may be `[]`). Each class follows the `docs/TOOL.md` design: inherits `BaseTool` and is decorated with `@tool`. |
| `CMD_HANDLERS` | `list[type]` | `CmdHandler` subclasses to register with the shell (may be `[]`). |

`name` and `on_start` are **required**; `SYSTEM_PROMPT`, `TOOLS` and
`CMD_HANDLERS` are optional and default to `""` / `[]` when absent.  If
`on_start` returns an error string (or raises), the plugin is still loaded
(tools/commands/prompt are registered) but the error is surfaced to the
user via `janito --list-plugins` and a startup warning.

---

## How Loading Works (sys.path)

Loading a plugin **temporarily** adds the plugin's **parent directory** to
the front of `sys.path`:

- The plugin directory itself is the package (it contains `__init__.py`),
  so its **parent** must be on `sys.path` for the package to import by its
  directory name (e.g. `importlib.import_module("janito-codesearch-plugin")`)
  and for **relative imports inside the plugin code** to resolve
  (`from . import index`, `from .tools.code_search import ...`,
  `from .cmd.codesearch_cmd import ...`).
- The plugin package and the modules it imports are loaded **while the
  entry is active**.  After loading, the entry is removed and `sys.path`
  is restored to its original state.

Because the `sys.path` entry is temporary, plugin modules that are used at
runtime (tools' `run()`, command handlers, `on_start`) must be **imported
during plugin load** (typically at the top of the plugin's `__init__.py`)
so they stay available in `sys.modules` after the entry is popped.

---

## Directory Layout

```
plugins/<name>/
    __init__.py          # contract symbols (name, on_start, SYSTEM_PROMPT, TOOLS, CMD_HANDLERS)
    tools/               # tool modules (docs/TOOL.md design)
        __init__.py
        <tool>.py
    cmd/                 # CmdHandler subclasses
        __init__.py
        <command>.py
    <engine modules>     # any other modules/packages the plugin needs
    tests/               # optional plugin-local tests
```

---

## Step-by-Step: A Minimal Plugin

Create `plugins/hello/`:

```python
# plugins/hello/__init__.py
name = "hello"

def on_start():
    print("hello plugin loaded")
    return None  # None = success

SYSTEM_PROMPT = "\n\nYou have access to the 'hello' plugin.\n"

TOOLS = []

CMD_HANDLERS = []
```

Load it:

```bash
janito --plugin plugins/hello "Hello!"
```

The plugin's `SYSTEM_PROMPT` is appended to the default system prompt.

---

## Loading Plugins

```bash
janito --plugin DIR            # load one plugin
janito --plugin DIR1 --plugin DIR2   # load several (repeatable)
janito --list-plugins          # show loaded plugins and on_start errors
janito --no-plugins            # do NOT autoload plugins from ~/.janito/plugins
```

Plugins installed in `~/.janito/plugins` (see
[Installing Plugins](#installing-plugins)) are **autoloaded** on every
janito run.  `--no-plugins` disables this autoload; plugins explicitly
requested with `--plugin DIR` are still loaded.

Plugins are loaded **after** CLI setup (privileges) and
**before** any registry/shell access, so plugin tools, commands and
system-prompt sections are all live by the time a session starts.  This
applies to single-prompt, interactive, and `--web` modes (web inherits
plugin tools and prompt sections automatically).

> **Note on `--no-tools`:** plugin tools are **not** affected by
> `--no-tools` (which only disables built-in tools).  Use `--no-plugins`
> to skip autoloading installed plugins.

---

## Installing Plugins

Plugins can be installed from a GitHub repository URL:

```bash
janito --install-plugin https://github.com/joaompinto/janito-codesearch-plugin
```

This downloads the repository's `master` branch as a zip archive and
extracts it to `~/.janito/plugins/<repo-name>` (honoring `-c/--config-dir`).
The plugin is then **autoloaded** on every subsequent janito run.

To uninstall a plugin (removes its directory from
`~/.janito/plugins/<repo-name>`):

```bash
janito --uninstall-plugin codesearch
```

The name is the plugin's **plugin name** (the `name` symbol the plugin
exports, as shown by `--list-plugins`) — for the codesearch plugin that is
`codesearch`, even though it installs to the
`janito-codesearch-plugin` directory.  A broken plugin that cannot be
imported is matched by its directory name as a fallback.

To temporarily disable autoloading without uninstalling:

```bash
janito --no-plugins
```

To see which plugins are currently loaded:

```bash
janito --list-plugins
```

Inside the interactive shell, `/plugins` lists the **installed** plugins
(scanned from `<config_dir>/plugins`, default `~/.janito/plugins`), their
paths and whether each one loaded in the current session.

---

## Available Plugins

The following plugins are available for janito. Install any of them with:

```bash
janito --install-plugin <url>
```

| Name | Purpose | URL |
|------|---------|-----|
| codesearch | Index source code for faster lookups on large repos | https://github.com/joaompinto/janito-codesearch-plugin |
| gmail | Gmail (IMAP) tools: read, count, delete, trash, move emails and list folders | https://github.com/joaompinto/janito-gmail-plugin |
| onedrive | Microsoft OneDrive tools: list, read, upload, download, delete files, create folders and share links | https://github.com/joaompinto/janito-onedrive-plugin |

---

## The codesearch Plugin (reference implementation)

The `CodeSearch` tool, the trigram engine, and the `/codesearch` shell
command live in the `../plugins/janito-codesearch-plugin/` plugin:

```
../plugins/janito-codesearch-plugin/
    __init__.py            # contract + on_start() that builds .janito/codesearch.db
    code_search.py         # CodeSearch engine
    index.py               # SQLite inverted trigram index
    trigram.py             # trigram extraction
    candidates.py          # candidate selection / line scanning
    tools/code_search.py   # the CodeSearch tool (docs/TOOL.md)
    cmd/codesearch_cmd.py  # /codesearch update | recreate
```

Load it with:

```bash
janito --plugin ../plugins/janito-codesearch-plugin
```

When the plugin loads, `on_start()` checks for `.janito/codesearch.db` in
the current working directory and **creates the index** if it is missing.

Shell usage:

```text
/codesearch update     # incrementally update the index (added/deleted/changed files)
/codesearch recreate   # rebuild the index from scratch
```

---

## Interacting with janito

From inside a plugin you can import any installed janito module:

```python
from janito.tooling import BaseTool, norm_path
from janito.tooling.decorator import tool
from janito.tooling.reporter import report_progress
from janito.shell.cmds.base import CmdHandler
from janito.shell.cmds.registry import register_command
```

Relative imports between the plugin's own modules use the usual dot
notation (`from . import x`, `from .tools.y import Z`).

---

## Checklist Before Submitting

- [ ] Plugin directory contains `__init__.py`.
- [ ] `name` and `on_start` are defined; `on_start` returns `None` or a string.
- [ ] `SYSTEM_PROMPT`, `TOOLS`, `CMD_HANDLERS` are defined (or defaulted).
- [ ] Tools follow the `docs/TOOL.md` design (`BaseTool` + `@tool`).
- [ ] All modules used at runtime are imported during load (top of `__init__.py`).
- [ ] `janito --plugin <dir>` loads the plugin with no errors.
- [ ] `janito --list-plugins` shows the plugin without `on_start` errors.
