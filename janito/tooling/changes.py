"""Track the tool executions that changed files during a session.

Whenever a *successful* tool call has ``filepath`` as its first argument, the
tool name and its invocation parameters are appended to a JSON-lines file
(``./.janito/changes.jsonl``, relative to the current working directory). Only
the parameters are recorded — never the tool's result. The file is meant to be
removed before a new user prompt is requested for processing, so it always
describes the changes made while handling the *current* prompt.

The :func:`/changes` interactive command reads this file back and renders each
recorded execution in a friendly, human-readable format:

* ``CreateFile`` — the written ``content`` is shown with rich syntax
  highlighting (the language is guessed from the file path).
* ``ReplaceTextInFile`` — a unified diff between ``old_str`` and ``new_str``
  is generated and shown, syntax-highlighted (again guessing the language from
  the file path).
* Any other tool — its parameters are shown as pretty-printed JSON.

Like :mod:`janito.tooling.tools_usage` and :mod:`janito.tooling.used_files`,
the recording functions here are deliberately defensive: tracking is a
best-effort side feature and must never be able to break tool execution or the
agent loop, so every access is wrapped and failures are swallowed.
"""

from __future__ import annotations

import difflib
import json
import logging
import threading
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Directory (relative to the current working directory) where the changes log
# lives. ``./.janito`` is the per-project workspace directory (it also holds
# the shell ``history.log``).
CHANGES_DIR = Path(".janito")

# Name of the JSON-lines file that records the tool executions.
CHANGES_FILENAME = "changes.jsonl"

# Name of the argument that, when it is the *first* argument of a tool call,
# marks the call as a file-changing execution worth tracking.
TRACKED_ARG_NAME = "filepath"

# Tool names that receive special rendering in the /changes command.
CREATE_FILE_TOOL = "CreateFile"
REPLACE_TEXT_TOOL = "ReplaceTextInFile"

# Serialises access from the multiple threads the web backend uses to run
# tools concurrently.
_lock = threading.Lock()


def get_changes_file_path() -> Path:
    """Return the path to the ``changes.jsonl`` file.

    The path is resolved relative to the current working directory, i.e.
    ``./.janito/changes.jsonl``.

    Returns:
        pathlib.Path: ``<cwd>/.janito/changes.jsonl``.
    """
    return Path.cwd() / CHANGES_DIR / CHANGES_FILENAME


def record_change(tool_name: str, tool_args: dict) -> None:
    """Record a file-changing tool execution to ``./.janito/changes.jsonl``.

    The execution is only recorded when ``tool_args`` is a non-empty mapping
    whose first key is :data:`TRACKED_ARG_NAME` (``"filepath"``). Only the
    parameters are stored (never the result). This function never raises; any
    I/O error is logged and ignored.

    Args:
        tool_name: The name of the tool that was invoked.
        tool_args: The arguments the tool was called with (insertion ordered).
    """
    try:
        if not tool_name or not isinstance(tool_args, dict) or not tool_args:
            return

        # The "first argument" is the first key of the (ordered) arguments.
        first_arg = next(iter(tool_args))
        if first_arg != TRACKED_ARG_NAME:
            return

        path = tool_args[first_arg]
        if not isinstance(path, str) or not path:
            return

        record = {"tool": tool_name, "params": tool_args}

        changes_path = get_changes_file_path()
        with _lock:
            changes_path.parent.mkdir(parents=True, exist_ok=True)
            with open(changes_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception as e:  # noqa: BLE001 - tracking must never break execution
        logger.debug(f"Failed to record change for '{tool_name}': {e}")


def clear_changes() -> bool:
    """Remove the ``changes.jsonl`` file (if it exists).

    Called before a new user prompt is requested for processing so that the
    file only describes the changes made while handling the current prompt.
    This function never raises.

    Returns:
        bool: ``True`` if a file was removed, ``False`` if there was nothing
            to remove (or removal failed).
    """
    try:
        with _lock:
            changes_path = get_changes_file_path()
            if changes_path.exists():
                changes_path.unlink()
                return True
            return False
    except Exception as e:  # noqa: BLE001 - tracking must never break execution
        logger.debug(f"Failed to clear changes file: {e}")
        return False


def load_changes() -> list[dict[str, Any]]:
    """Read back every recorded change from ``./.janito/changes.jsonl``.

    Returns:
        list[dict[str, Any]]: One ``{"tool": str, "params": dict}`` record per
            line, in the order they were written. Empty if the file does not
            exist or cannot be read. Malformed lines are skipped.
    """
    records: list[dict[str, Any]] = []
    try:
        changes_path = get_changes_file_path()
        if not changes_path.exists():
            return records
        with _lock:
            with open(changes_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                    except json.JSONDecodeError:
                        logger.debug(f"Skipping malformed changes line: {line!r}")
                        continue
                    if isinstance(record, dict):
                        records.append(record)
    except Exception as e:  # noqa: BLE001 - tracking must never break execution
        logger.debug(f"Failed to load changes file: {e}")
    return records


def _guess_lexer(path: str, code: str) -> str:
    """Guess a Pygments lexer name for ``code`` based on ``path``.

    Falls back to ``"text"`` when rich cannot guess a lexer, so syntax
    highlighting degrades gracefully instead of raising.
    """
    try:
        from rich.syntax import Syntax

        return Syntax.guess_lexer(path, code) or "text"
    except Exception:  # noqa: BLE001 - highlighting must never break the report
        return "text"


def _build_replace_diff(old_str: str, new_str: str) -> str:
    """Build a unified diff between ``old_str`` and ``new_str``.

    Args:
        old_str: The text that was searched for.
        new_str: The replacement text.

    Returns:
        str: A unified diff (without trailing line terminators) suitable for
            syntax-highlighted display.
    """
    old_lines = old_str.splitlines()
    new_lines = new_str.splitlines()
    diff = difflib.unified_diff(
        old_lines,
        new_lines,
        fromfile="before",
        tofile="after",
        lineterm="",
    )
    return "\n".join(diff)


def render_changes(console=None) -> None:
    """Render the recorded changes to ``console`` in a friendly format.

    * ``CreateFile`` — shows the ``content`` with rich syntax highlighting.
    * ``ReplaceTextInFile`` — shows a syntax-highlighted diff between
      ``old_str`` and ``new_str``.
    * Anything else — shows the parameters as pretty-printed JSON.

    A friendly message is printed when no changes have been recorded. This
    function never raises.

    Args:
        console: Optional ``rich.console.Console`` to print to. A fresh one is
            created when not provided.
    """
    try:
        from rich.console import Console
        from rich.markup import escape
        from rich.panel import Panel
        from rich.syntax import Syntax
        from rich.text import Text

        if console is None:
            console = Console()

        records = load_changes()
        changes_path = get_changes_file_path()

        if not records:
            console.print("No changes recorded for the current prompt.")
            console.print(f"[dim](changes file: {changes_path})[/dim]")
            return

        header = Text()
        header.append("\n===== Changes =====", style="cyan")
        console.print(header, highlight=False)

        for index, record in enumerate(records, start=1):
            tool_name = record.get("tool", "<unknown>")
            params = record.get("params", {})
            if not isinstance(params, dict):
                params = {}

            # Display the file path relative to the CWD when possible.
            filepath = params.get(TRACKED_ARG_NAME, "")
            try:
                from .path_utils import norm_path

                display_path = norm_path(filepath) if filepath else "<no filepath>"
            except Exception:  # noqa: BLE001 - display must never break the report
                display_path = filepath or "<no filepath>"

            title = (
                f"[bold]#{index}[/bold] [green]{tool_name}[/green] "
                f"{escape(display_path)}"
            )
            console.print()
            console.print(Panel(title, border_style="cyan", padding=(0, 1)))

            if tool_name == CREATE_FILE_TOOL:
                content = params.get("content", "")
                lexer = _guess_lexer(str(filepath), content)
                console.print(
                    Syntax(content or "", lexer, line_numbers=True, word_wrap=True)
                )
            elif tool_name == REPLACE_TEXT_TOOL:
                old_str = params.get("old_str", "")
                new_str = params.get("new_str", "")
                diff_text = _build_replace_diff(old_str, new_str)
                lexer = _guess_lexer(str(filepath), diff_text)
                console.print(
                    Syntax(diff_text or "", lexer, line_numbers=False, word_wrap=True)
                )
            else:
                # Show the parameters as a pretty-printed, syntax-highlighted
                # JSON block for a readable summary.
                params_json = json.dumps(params, ensure_ascii=False, indent=2)
                console.print(
                    Syntax(params_json, "json", line_numbers=False, word_wrap=True)
                )
    except Exception as e:  # noqa: BLE001 - reporting must never break the shell
        logger.debug(f"Failed to render changes: {e}")
        if console is not None:
            try:
                console.print(f"[red]Failed to render changes: {e}[/red]")
            except Exception:  # noqa: BLE001
                pass


__all__ = [
    "CHANGES_DIR",
    "CHANGES_FILENAME",
    "TRACKED_ARG_NAME",
    "CREATE_FILE_TOOL",
    "REPLACE_TEXT_TOOL",
    "get_changes_file_path",
    "record_change",
    "clear_changes",
    "load_changes",
    "render_changes",
]
