"""Code search index initialization CLI handler."""

from pathlib import Path

from ...codesearch import CodeSearch

# Name of the SQLite index database stored in the working directory's
# .janito folder (alongside history.log, changes.jsonl and sessions/).
INDEX_DB_FILENAME = "codesearch.db"


def handle_init_codesearch(args) -> int:
    """Handle --init-codesearch command.

    Builds a trigram code search index over the current working directory
    and stores it at ``./.janito/codesearch.db``, then exits.

    Args:
        args: Parsed command line arguments (unused).

    Returns:
        int: Exit code (0 on success).
    """
    source_path = Path.cwd()
    index_db_path = source_path / ".janito" / INDEX_DB_FILENAME
    index_db_path.parent.mkdir(parents=True, exist_ok=True)

    print("Indexing the current directory, this may take some time...")

    with CodeSearch(str(source_path), str(index_db_path)) as cs:
        cs.Create()
        stats = cs.stats()

    print(f"Code search index created at {index_db_path}")
    print(
        f"Indexed {stats['file_count']} files "
        f"({stats['trigram_count']} trigrams) from {source_path}"
    )
    return 0
