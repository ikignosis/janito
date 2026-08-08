"""Track which files were READ and WRITE by tool calls during a prompt.

Whenever a tool is invoked whose *first* argument is named ``filepath``, the
value of that argument is recorded in one (or both) of two lists \u2014 ``READ``
and ``WRITE`` \u2014 depending on the tool's declared permissions. The permissions
string is the one set by the ``@tool(permissions="\u2026")`` decorator (e.g.
``"r"``, ``"w"``, ``"rw"``):

* if it contains ``'r'`` the path is appended to the ``READ`` list;
* if it contains ``'w'`` the path is appended to the ``WRITE`` list.

Filenames are unique within each list: a path already present is not added
again. The lists are kept in memory for the lifetime of the process and can be
rendered as a ``Used files`` report that is printed (via ``rich``) before the
token-usage summary.

:class:`UsedFilesTracker` implements the tracking logic (the module functions
below delegate to a module-level singleton).  Like
:mod:`janito.tooling.tools_usage` and :mod:`janito.tooling.changes`, tracking
is deliberately defensive: it is a best-effort side feature and must never be
able to break tool execution or the agent loop, so every access is wrapped and
failures are swallowed.
"""

from __future__ import annotations

import logging
import threading

from rich.text import Text

from .path_utils import norm_path

logger = logging.getLogger(__name__)

# Name of the argument that, when it is the *first* argument of a tool call,
# marks the call as operating on a file path worth tracking.
TRACKED_ARG_NAME = "filepath"


class UsedFilesTracker:
    """Track the file paths READ and WRITE by tool calls during a prompt.

    The tracker keeps two in-memory lists (``READ`` / ``WRITE``) of unique
    file paths, populated from tool calls whose first argument is named
    ``filepath`` according to the tool's declared permissions (see
    :meth:`record`).  :meth:`snapshot` returns a copy, :meth:`reset` clears
    the state, and :meth:`format` renders the ``Used files`` report.
    """

    def __init__(self) -> None:
        # Serialises access from the multiple threads the web backend uses to
        # run tools concurrently.
        self._lock = threading.Lock()
        # The two tracked lists. A path is appended to READ when the tool's
        # permissions contain 'r' and to WRITE when they contain 'w'.
        self._used_files: dict[str, list[str]] = {"READ": [], "WRITE": []}

    def record(self, tool_name: str, tool_args: dict) -> None:
        """Record a file path used by a tool call, if applicable.

        The call is only tracked when ``tool_args`` is a non-empty mapping
        whose first key is :data:`TRACKED_ARG_NAME` (``"filepath"``) and whose
        value is a non-empty string. The path is appended to the ``READ`` list
        when the tool's permissions contain ``'r'`` and to the ``WRITE`` list
        when they contain ``'w'``. Filenames are unique per list: a path
        already present is not added again. This method never raises.

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

            permissions = self._get_permissions(tool_name)

            with self._lock:
                if "r" in permissions and path not in self._used_files["READ"]:
                    self._used_files["READ"].append(path)
                if "w" in permissions and path not in self._used_files["WRITE"]:
                    self._used_files["WRITE"].append(path)
        except Exception as e:  # noqa: BLE001 - tracking must never break execution
            logger.debug(f"Failed to record used file for '{tool_name}': {e}")

    def snapshot(self) -> dict[str, list[str]]:
        """Return a copy of the tracked ``{"READ": [...], "WRITE": [...]}`` mapping.

        Returns:
            dict[str, list[str]]: A snapshot of the used files, in insertion order.
        """
        with self._lock:
            return {key: list(paths) for key, paths in self._used_files.items()}

    def reset(self) -> None:
        """Clear all tracked used files (e.g. at the start of a new prompt)."""
        with self._lock:
            for paths in self._used_files.values():
                paths.clear()

    def format(self) -> Text:
        """Render the tracked used files as a printable ``Used files`` report.

        The report is preceded by a blank line (to visually separate it from
        the answer) and uses the following layout, rendered via
        :class:`rich.text.Text`::

            <blank line>
            Used files
            ----------
            <n> read : file1, file2
            <n> write : file1, file2

        where ``<n>`` is the number of entries in the respective list. Each
        path is displayed through
        :func:`~janito.tooling.path_utils.norm_path`, so paths located under
        the current working directory are shown relative to it (e.g.
        ``./subdir/file.py``) rather than as absolute paths. Paths outside the
        working directory are left unchanged.

        A ``read``/``write`` line is omitted entirely when its list is empty,
        so a prompt that only read files shows just the ``read`` line (and
        vice-versa). When nothing has been tracked (both lists empty), an
        empty :class:`~rich.text.Text` is returned so that no header is
        printed at all.

        Returns:
            rich.text.Text: The multi-line report, or an empty ``Text`` when no
            files were tracked.
        """
        used = self.snapshot()
        read_paths = used.get("READ", [])
        write_paths = used.get("WRITE", [])

        if not read_paths and not write_paths:
            return Text()

        def _display(path: str) -> str:
            # Display paths relative to the current working directory when
            # possible (via ``norm_path``), falling back to the raw recorded
            # path if normalization fails for any reason.
            try:
                return norm_path(path)
            except Exception:  # noqa: BLE001 - display must never break the report
                return path

        text = Text()
        text.append("\nUsed files", style="cyan")
        text.append("\n----------")
        if read_paths:
            text.append(
                f"\n{len(read_paths)} read : {', '.join(_display(p) for p in read_paths)}"
            )
        if write_paths:
            text.append(
                f"\n{len(write_paths)} write : "
                f"{', '.join(_display(p) for p in write_paths)}"
            )
        return text

    @staticmethod
    def _get_permissions(tool_name: str) -> str:
        """Return the permission string declared for ``tool_name``.

        Delegates to :func:`~janito.tooling.tools_registry.get_tool_permissions`,
        which reads the ``_tool_permissions`` attribute the ``@tool`` decorator
        sets on the registered callable. Returns an empty string when the tool
        is not in the registry or declares no permissions. Never raises.
        """
        try:
            from .tools_registry import get_tool_permissions

            return get_tool_permissions(tool_name) or ""
        except Exception as e:  # noqa: BLE001 - tracking must never break execution
            logger.debug(f"Failed to read permissions for '{tool_name}': {e}")
            return ""


# Module-level singleton tracker backing the functions below.
_tracker = UsedFilesTracker()


def record_used_file(tool_name: str, tool_args: dict) -> None:
    """Record a file path used by a tool call, if applicable.

    The call is only tracked when ``tool_args`` is a non-empty mapping whose
    first key is :data:`TRACKED_ARG_NAME` (``"filepath"``) and whose value is a
    non-empty string. The path is appended to the ``READ`` list when the tool's
    permissions contain ``'r'`` and to the ``WRITE`` list when they contain
    ``'w'``. Filenames are unique per list: a path already present is not added
    again. This function never raises.

    Args:
        tool_name: The name of the tool that was invoked.
        tool_args: The arguments the tool was called with (insertion ordered).
    """
    _tracker.record(tool_name, tool_args)


def get_used_files() -> dict[str, list[str]]:
    """Return a copy of the tracked ``{"READ": [...], "WRITE": [...]}`` mapping.

    Returns:
        dict[str, list[str]]: A snapshot of the used files, in insertion order.
    """
    return _tracker.snapshot()


def reset_used_files() -> None:
    """Clear all tracked used files (e.g. at the start of a new prompt)."""
    _tracker.reset()


def format_used_files() -> Text:
    """Render the tracked used files as a printable ``Used files`` report.

    The report is preceded by a blank line (to visually separate it from the
    answer) and uses the following layout, rendered via :class:`rich.text.Text`::

        <blank line>
        Used files
        ----------
        <n> read : file1, file2
        <n> write : file1, file2

    where ``<n>`` is the number of entries in the respective list. Each path is
    displayed through :func:`~janito.tooling.path_utils.norm_path`, so paths
    located under the current working directory are shown relative to it (e.g.
    ``./subdir/file.py``) rather than as absolute paths. Paths outside the
    working directory are left unchanged.

    A ``read``/``write`` line is omitted entirely when its list is empty, so a
    prompt that only read files shows just the ``read`` line (and vice-versa).
    When nothing has been tracked (both lists empty), an empty
    :class:`~rich.text.Text` is returned so that no header is printed at all.

    Returns:
        rich.text.Text: The multi-line report, or an empty ``Text`` when no
        files were tracked.
    """
    return _tracker.format()


__all__ = [
    "TRACKED_ARG_NAME",
    "UsedFilesTracker",
    "record_used_file",
    "get_used_files",
    "reset_used_files",
    "format_used_files",
]
