"""codesearch plugin - /codesearch shell command handler.

Usage:
    /codesearch update     - Incrementally update the index
    /codesearch recreate   - Rebuild the index from scratch
"""

from pathlib import Path

from janito.shell.cmds.base import CmdHandler

from ..code_search import CodeSearch

INDEX_DB_RELPATH = Path(".janito") / "codesearch.db"


class CodesearchCmdHandler(CmdHandler):
    """Command handler for /codesearch."""

    @property
    def name(self) -> str:
        return "/codesearch"

    def handle(self, shell, user_input: str) -> bool:
        """Handle the /codesearch command.

        Args:
            shell: The interactive shell instance.
            user_input: The raw user input.

        Returns:
            True if the input was a /codesearch command, False otherwise.
        """
        if not user_input.lower().startswith(self.name.lower()):
            return False

        parts = user_input.strip().split()
        if len(parts) == 1:
            self._print_usage()
            return True

        subcommand = parts[1].lower()
        if subcommand == "update":
            self._update()
        elif subcommand == "recreate":
            self._recreate()
        elif subcommand == "help":
            self._print_usage()
        else:
            print(f"Unknown /codesearch subcommand: {subcommand}")
            self._print_usage()
        return True

    def _index_db_path(self) -> Path:
        """The index database path for the current working directory."""
        return Path.cwd() / INDEX_DB_RELPATH

    def _update(self) -> None:
        """Incrementally update the index (added/deleted/changed files)."""
        db = self._index_db_path()
        if not db.is_file():
            print(
                f"Error: no code search index at {db} "
                "(run /codesearch recreate to create it)"
            )
            return
        print("Updating code search index...")
        with CodeSearch(str(Path.cwd()), str(db)) as cs:
            cs.Update()
            stats = cs.stats()
        print(
            f"Code search index updated: {stats['file_count']} files "
            f"({stats['trigram_count']} trigrams)"
        )

    def _recreate(self) -> None:
        """Rebuild the index from scratch."""
        db = self._index_db_path()
        db.parent.mkdir(parents=True, exist_ok=True)
        print("Recreating code search index, this may take some time...")
        with CodeSearch(str(Path.cwd()), str(db)) as cs:
            cs.Create()
            stats = cs.stats()
        print(
            f"Code search index recreated at {db}: {stats['file_count']} files "
            f"({stats['trigram_count']} trigrams)"
        )

    def _print_usage(self) -> None:
        """Print usage information for /codesearch."""
        print("Usage:")
        print("  /codesearch update    - Incrementally update the index")
        print("                         (added/deleted/changed files)")
        print("  /codesearch recreate  - Rebuild the index from scratch")
        print(
            "  /codesearch help      - Show this help "
            "(the index is created automatically when the plugin loads)"
        )


# Registered by the plugin manager via the plugin's CMD_HANDLERS list.
