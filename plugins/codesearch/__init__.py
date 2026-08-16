"""codesearch plugin - trigram-based code search.

This plugin provides:

- ``CodeSearch`` — the tool that queries the per-project SQLite trigram
  index at ``./.janito/codesearch.db`` (per ``docs/TOOL.md``).
- ``/codesearch`` — a shell command to maintain the index:
  ``/codesearch update`` (incremental) and ``/codesearch recreate``.

When the plugin loads (``on_start``), if there is no
``./.janito/codesearch.db`` in the current working directory, the index is
created automatically.
"""

from pathlib import Path

from .candidates import MATCH, CodeSearchMatch
from .code_search import CodeSearch

name = "codesearch"

# Per-project location of the SQLite index (same location the old
# ``janito --init-codesearch`` flag used).
INDEX_DB_RELPATH = Path(".janito") / "codesearch.db"

SYSTEM_PROMPT = (
    "When searching text on files use the CodeSearch tool before the other "
    "search tools"
)


def on_start() -> str | None:
    """Create the code search index when missing; None on success.

    Returns:
        None on success, or a string describing the error (surfaced by
        ``janito --list-plugins``).
    """
    index_db_path = Path.cwd() / INDEX_DB_RELPATH
    if index_db_path.is_file():
        return None
    try:
        index_db_path.parent.mkdir(parents=True, exist_ok=True)
        print(
            "codesearch: no index at ./.janito/codesearch.db, "
            "building it (this may take some time)..."
        )
        with CodeSearch(str(Path.cwd()), str(index_db_path)) as cs:
            cs.Create()
        return None
    except Exception as e:  # noqa: BLE001 - surfaced as a plugin load error
        return f"failed to create code search index at {index_db_path}: {e}"


# Imported after the engine so ``..code_search`` module imports inside the
# tool / command modules resolve cleanly (the package __init__ runs first).
from .cmd.codesearch_cmd import CodesearchCmdHandler  # noqa: E402
from .tools.code_search import CodeSearch as CodeSearchTool  # noqa: E402

TOOLS = [CodeSearchTool]
CMD_HANDLERS = [CodesearchCmdHandler]

__all__ = [
    "name",
    "on_start",
    "SYSTEM_PROMPT",
    "TOOLS",
    "CMD_HANDLERS",
    "CodeSearch",
    "MATCH",
    "CodeSearchMatch",
    "INDEX_DB_RELPATH",
]
