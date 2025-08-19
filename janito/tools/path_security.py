"""janito.tools.path_security
================================
Utilities that ensure user-supplied file-system paths never escape the allowed
workspace.

Public interface
----------------

``is_path_within_workdir(path, workdir)``
    Verify that *path* is located **inside** *workdir* (or equals it).  If
    *workdir* is *None* every path is accepted.

``validate_paths_in_arguments(arguments, workdir, *, schema=None)``
    Inspect a mapping of arguments (typically the kwargs that will later be
    passed to a tool adapter).  Any item whose key *looks* like it refers to a
    path is validated with :func:`is_path_within_workdir`.  If a JSON Schema for
    the tool is provided, the keys that explicitly represent paths are derived
    from it.  Otherwise a simple heuristic based on the key name is used.

Both helpers raise :class:`PathSecurityError` if a path tries to escape the
workspace.
"""

from __future__ import annotations

import os
from typing import Any, Mapping

__all__ = [
    "PathSecurityError",
    "is_path_within_workdir",
    "validate_paths_in_arguments",
]


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class PathSecurityError(Exception):
    """Raised when an argument references a location outside the workspace."""


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------


def is_path_within_workdir(
    path: str, workdir: str | None
) -> (
    bool
):  # noqa: D401 – we start with an imperative verb  # noqa: D401 – we start with an imperative verb
    """Return *True* if *path* is located inside *workdir* (or equals it).

    Relative *path*s are **resolved relative to the *workdir***, *not* to the
    current working directory.  This behaviour makes the security checks
    deterministic regardless of the directory from which the Python process was
    started.

    Implementation details
    ----------------------
    The function converts both *workdir* and *path* to absolute paths and then
    uses :func:`os.path.commonpath` to determine the longest common sub-path.  A
    path is considered *inside* the workspace when that common part equals the
    workspace directory itself.
    """
    if not workdir:
        # No workdir configured – everything is implicitly allowed.
        return True

    abs_workdir = os.path.abspath(workdir)

    # Resolve *path* – if it is *relative* we interpret it **relative to the
    # workspace** (and *not* to the current working directory!) so that a value
    # like '.' always points inside the workspace.
    if os.path.isabs(path):
        abs_path = os.path.abspath(path)
    else:
        abs_path = os.path.abspath(os.path.join(abs_workdir, path))

    try:
        common_part = os.path.commonpath([abs_workdir, abs_path])
    except ValueError:
        # On Windows different drive letters cause ValueError → definitely
        # outside the workspace.
        return False

    # Additionally allow files located inside the system temporary directory.
    import tempfile

    abs_tempdir = os.path.abspath(tempfile.gettempdir())
    try:
        common_temp = os.path.commonpath([abs_tempdir, abs_path])
    except ValueError:
        common_temp = None
    if common_temp == abs_tempdir:
        return True

    return common_part == abs_workdir


# ---------------------------------------------------------------------------
# Helper for tool adapters
# ---------------------------------------------------------------------------


def _looks_like_path_key(key: str) -> bool:
    """Return *True* when *key* likely refers to a file-system path."""
    key_lower = key.lower()
    if key_lower in {
        "path",
        "paths",
        "filepath",
        "file",
        "filename",
        "directory",
        "directories",
        "dir",
        "dirs",
        "target",
        "targets",
        "source",
        "sources",
    }:
        return True

    common_suffixes = ("path", "paths", "file", "dir", "dirs")
    return key_lower.endswith(common_suffixes)


def _extract_path_keys_from_schema(schema: Mapping[str, Any]) -> set[str]:
    """Extract keys that represent paths from the provided JSON schema."""
    path_keys: set[str] = set()
    if schema is not None:
        for k, v in schema.get("properties", {}).items():
            # Handle direct path strings
            if v.get("format") == "path" or (
                v.get("type") == "string"
                and (
                    "path" in v.get("description", "").lower()
                    or k.endswith("path")
                    or k == "path"
                )
            ):
                path_keys.add(k)
            # Handle arrays of path strings
            elif v.get("type") == "array" and "items" in v:
                items = v["items"]
                if items.get("format") == "path" or (
                    items.get("type") == "string"
                    and (
                        "path" in items.get("description", "").lower()
                        or "path" in v.get("description", "").lower()
                        or k.endswith("paths")
                        or k == "paths"
                    )
                ):
                    path_keys.add(k)
    return path_keys


def _validate_argument_value(key: str, value: Any, workdir: str) -> None:
    """Validate a single argument value (string or list of strings) for path security."""
    # Single string argument → validate directly.
    if isinstance(value, str) and value.strip():
        if not is_path_within_workdir(value, workdir):
            _raise_outside_workspace_error(key, value, workdir)
    # Sequence of potential paths → validate every item.
    elif isinstance(value, list):
        for item in value:
            if isinstance(item, str) and item.strip():
                if not is_path_within_workdir(item, workdir):
                    _raise_outside_workspace_error(key, item, workdir)


def validate_paths_in_arguments(
    arguments: Mapping[str, Any] | None,
    workdir: str | None,
    *,
    schema: Mapping[str, Any] | None = None,
) -> None:
    """Ensure every *path-looking* value in *arguments* is inside *workdir*.

    The function walks through *arguments* and raises :class:`PathSecurityError`
    if it finds a suspicious path that points outside the allowed workspace.

    If *schema* is given it is expected to be the JSON Schema describing the
    tool's arguments (as produced by ``janito.tools.inspect_registry``).  Keys
    whose schema declares a ``"format": "path"`` or mentions "path" in the
    description are treated as path parameters.  Without a schema the function
    falls back to a simple heuristic based on the argument name.
    """
    if not workdir or not arguments:
        return

    path_keys = _extract_path_keys_from_schema(schema) if schema is not None else set()

    for key, value in arguments.items():
        key_is_path = key in path_keys or _looks_like_path_key(key)
        if not key_is_path:
            continue
        _validate_argument_value(key, value, workdir)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _raise_outside_workspace_error(
    key: str, path: str, workdir: str
) -> None:  # noqa: D401
    """Raise a consistent :class:`PathSecurityError` for *path*."""
    abs_workdir = os.path.abspath(workdir)
    attempted = (
        os.path.abspath(path)
        if os.path.isabs(path)
        else os.path.abspath(os.path.join(abs_workdir, path))
    )
    raise PathSecurityError(
        f"Argument '{key}' path '{path}' is not within allowed workdir '{workdir}' "
        f"[attempted path: {attempted}]"
    )
