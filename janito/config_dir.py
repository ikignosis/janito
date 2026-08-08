"""
Centralized configuration directory management for Janito CLI.

All Janito configuration (config.json, auth.json, secrets.json,
mcp_services.json and the skills directory) lives under a single base
directory. By default this is ``~/.janito`` but it can be overridden at
runtime with the ``-c`` / ``--config-dir`` CLI flag (see :func:`set_config_dir`).

A project-local mode can be enabled with the ``-l`` / ``--local`` CLI flag (see
:func:`set_local_config_mode`): configuration is then written to ``./.janito``
(the current working directory) instead of the base directory, and *reads*
resolve the local directory first, falling back to the base directory (global
``~/.janito`` or the ``-c`` override) for anything not stored locally.

This module intentionally has no dependencies on other janito modules so that
it can be imported from any configuration module without risking circular
imports.
"""

from pathlib import Path

# Default base configuration directory. This is the value used when -c/--config-dir
# is not provided on the command line.
DEFAULT_CONFIG_DIR = Path.home() / ".janito"

# The effective configuration directory. Updated by :func:`set_config_dir` when
# the user passes -c/--config-dir. Defaults to :data:`DEFAULT_CONFIG_DIR`.
_config_dir: Path = DEFAULT_CONFIG_DIR

# Whether -l/--local was passed: configuration is stored in ./.janito (the
# current working directory) and read with local-first priority.
_local_mode: bool = False


def get_local_config_dir() -> Path:
    """Get the project-local configuration directory (``./.janito``).

    The directory is resolved from the current working directory each time it
    is queried so that it always points at the project the user invoked
    janito from.

    Returns:
        Path: ``<cwd>/.janito``
    """
    return Path.cwd() / ".janito"


def set_config_dir(path: str | None) -> None:
    """Set the base configuration directory.

    Called early in ``main()`` when the ``-c`` / ``--config-dir`` flag is used.
    All configuration, auth and secret files are then stored/read from this
    directory instead of ``~/.janito``.

    Args:
        path: The directory to use as the base configuration directory. If
            ``None`` or empty, this is a no-op and the current directory is kept.
    """
    global _config_dir
    if not path:
        return
    _config_dir = Path(path).expanduser()


def set_local_config_mode(enabled: bool) -> None:
    """Enable or disable ``-l`` / ``--local`` mode.

    Called early in ``main()`` when the ``-l`` / ``--local`` flag is used. In
    local mode the project-local directory (``./.janito``) becomes the write
    target for all configuration and is resolved with priority over the base
    directory (see :func:`get_config_dirs`).

    Args:
        enabled: Whether local mode should be active.
    """
    global _local_mode
    _local_mode = bool(enabled)


def get_config_dir() -> Path:
    """Get the effective base configuration directory (the write target).

    In local mode this returns the project-local ``./.janito`` directory;
    otherwise it returns ``~/.janito`` (or the value set via
    :func:`set_config_dir`).

    Returns:
        Path: The directory that new/updated configuration is written to.
    """
    if _local_mode:
        return get_local_config_dir()
    return _config_dir


def get_config_dirs() -> list[Path]:
    """Get the configuration directories used for resolution, in priority order.

    When ``-l`` / ``--local`` is active the project-local directory
    (``./.janito``) comes first and the base directory (global ``~/.janito`` or
    the ``-c`` / ``--config-dir`` override) is the fallback. Otherwise only the
    base directory is used.

    Returns:
        List of directories to consult, highest priority first.
    """
    if not _local_mode:
        return [_config_dir]
    dirs = [get_local_config_dir()]
    if _config_dir != dirs[0]:
        dirs.append(_config_dir)
    return dirs


def get_config_file_path(name: str) -> Path:
    """Get the primary (write) path for a configuration file by name.

    Args:
        name: The file name (e.g. ``"auth.json"``).

    Returns:
        Path: ``<write dir>/<name>``.
    """
    return get_config_dir() / name


def get_config_file_paths(name: str) -> list[Path]:
    """Get all paths for a configuration file, in resolution priority order.

    When ``-l`` / ``--local`` is active the first entry is the project-local
    path (``./.janito/<name>``) followed by the base path
    (``~/.janito/<name>`` or the ``-c`` override); otherwise only the base path
    is returned.

    Args:
        name: The file name (e.g. ``"auth.json"``).

    Returns:
        List of paths, highest priority first.
    """
    return [d / name for d in get_config_dirs()]
