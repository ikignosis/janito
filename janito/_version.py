"""Version handling for Janito.
Attempts to obtain the package version in the following order:
1. If a janito.version module exists (generated when the package is built with
   setuptools-scm), use the version attribute from that module.
2. Ask importlib.metadata for the installed distribution version – works for
   both regular and editable installs handled by pip.
3. Fall back to calling setuptools_scm.get_version() directly, using the git
   repository when running from source without an installed distribution.
4. If everything else fails, return the literal string ``"unknown"`` so that
   the application continues to work even when the version cannot be
   determined.

This layered approach guarantees that a meaningful version string is returned
in most development and production scenarios while keeping Janito free from
hard-coded version numbers.
"""

from __future__ import annotations

import pathlib
from importlib import metadata as importlib_metadata

__all__ = ["__version__"]


# 1. "janito.version" (generated at build time by setuptools-scm)
try:
    from . import version as _generated_version  # type: ignore

    __version__: str = _generated_version.version  # pytype: disable=module-attr
except ImportError:  # pragma: no cover – not available in editable installs

    def _resolve_version() -> str:
        """Resolve the version string using several fallbacks."""

        # 2. importlib.metadata – works for both regular and `uv pip install -e`.
        try:
            return importlib_metadata.version("janito")
        except importlib_metadata.PackageNotFoundError:
            pass  # Not installed – probably running from a source checkout.

        # 3. setuptools_scm – query the VCS metadata directly.
        try:
            from setuptools_scm import get_version  # Imported lazily.

            package_root = pathlib.Path(__file__).resolve().parent.parent
            return get_version(root=str(package_root), relative_to=__file__)
        except Exception:  # pragma: no cover – any failure here falls through
            # Either setuptools_scm is not available or this is not a git repo.
            pass

        # 4. Ultimate fallback – return a placeholder.
        return "unknown"

    __version__ = _resolve_version()
