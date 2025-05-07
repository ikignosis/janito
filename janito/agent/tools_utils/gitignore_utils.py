import os
import pathspec


class GitignoreFilter:
    """
    Utility class for loading, interpreting, and applying .gitignore patterns to file and directory paths.

    Methods
    -------
    __init__(self, gitignore_path: str = ".gitignore")
        Loads and parses .gitignore patterns from the specified path or finds the nearest .gitignore if a directory is given.

    is_ignored(self, path: str) -> bool
        Returns True if the given path matches any of the loaded .gitignore patterns.

    filter_ignored(self, root: str, dirs: list, files: list) -> tuple[list, list]
        Filters out ignored directories and files from the provided lists, returning only those not ignored.
    """

    @staticmethod
    def find_nearest_gitignore(start_path):
        """
        Search upward from start_path for the nearest .gitignore file.
        Returns the path to the found .gitignore, or the default .gitignore in start_path if none found.
        """
        current_dir = os.path.abspath(start_path)
        if os.path.isfile(current_dir):
            current_dir = os.path.dirname(current_dir)
        while True:
            candidate = os.path.join(current_dir, ".gitignore")
            if os.path.isfile(candidate):
                return candidate
            parent = os.path.dirname(current_dir)
            if parent == current_dir:
                # Reached filesystem root, return default .gitignore path (may not exist)
                return os.path.join(start_path, ".gitignore")
            current_dir = parent

    def __init__(self, gitignore_path: str = ".gitignore"):
        # If a directory is passed, find the nearest .gitignore up the tree
        if os.path.isdir(gitignore_path):
            self.gitignore_path = self.find_nearest_gitignore(gitignore_path)
        else:
            self.gitignore_path = os.path.abspath(gitignore_path)
        self.base_dir = os.path.dirname(self.gitignore_path)
        lines = []
        if not os.path.exists(self.gitignore_path):
            self._spec = pathspec.PathSpec.from_lines("gitwildmatch", [])
        else:
            with open(
                self.gitignore_path, "r", encoding="utf-8", errors="replace"
            ) as f:
                lines = f.readlines()
            self._spec = pathspec.PathSpec.from_lines("gitwildmatch", lines)
        # Collect directory patterns (ending with /)
        self.dir_patterns = [
            line.strip() for line in lines if line.strip().endswith("/")
        ]

    def is_ignored(self, path: str) -> bool:
        """Return True if the given path is ignored by the loaded .gitignore patterns."""
        abs_path = os.path.abspath(path)
        rel_path = os.path.relpath(abs_path, self.base_dir).replace(os.sep, "/")
        return self._spec.match_file(rel_path)

    def filter_ignored(self, root: str, dirs: list, files: list) -> tuple[list, list]:
        """
        Filter out ignored directories and files from the provided lists.
        Always ignores the .git directory (like git does).
        """

        def dir_is_ignored(d):
            abs_path = os.path.abspath(os.path.join(root, d))
            rel_path = os.path.relpath(abs_path, self.base_dir).replace(os.sep, "/")
            if rel_path == ".git" or rel_path.startswith(".git/"):
                return True
            # Remove directory if it matches a directory pattern
            for pat in self.dir_patterns:
                pat_clean = pat.rstrip("/")
                if rel_path == pat_clean or rel_path.startswith(pat_clean + "/"):
                    return True
            return self._spec.match_file(rel_path)

        def file_is_ignored(f):
            abs_path = os.path.abspath(os.path.join(root, f))
            rel_path = os.path.relpath(abs_path, self.base_dir).replace(os.sep, "/")
            return self._spec.match_file(rel_path)

        dirs[:] = [d for d in dirs if not dir_is_ignored(d)]
        files = [f for f in files if not file_is_ignored(f)]
        return dirs, files
