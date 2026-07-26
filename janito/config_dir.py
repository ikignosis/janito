"""
Centralized configuration directory management for Janito CLI.

All Janito configuration (config.json, auth.json, secrets.json,
mcp_services.json and the skills directory) lives under a single base
directory. By default this is ``~/.janito`` but it can be overridden at
runtime with the ``-c`` / ``--config-dir`` CLI flag (see :func:`set_config_dir`).

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


def get_config_dir() -> Path:
    """Get the effective base configuration directory.

    Returns:
        Path: The configuration directory (``~/.janito`` by default, or the
            value set via :func:`set_config_dir`).
    """
    return _config_dir
