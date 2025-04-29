import os
from .gitignore_utils import filter_ignored


def walk_dir_with_gitignore(root_dir, max_depth=None):
    """
    Walks the directory tree starting at root_dir, yielding (root, dirs, files) tuples,
    with .gitignore rules applied.
    - If max_depth is None, unlimited recursion.
    - If max_depth=0, only the top-level directory (flat, no recursion).
    - If max_depth=1, only the root directory (matches 'find . -maxdepth 1').
    - If max_depth=N (N>1), yields files in root and up to N-1 levels below root (matches 'find . -maxdepth N').
    """
    for root, dirs, files in os.walk(root_dir):
        rel_path = os.path.relpath(root, root_dir)
        depth = 0 if rel_path == "." else rel_path.count(os.sep) + 1
        if max_depth is not None:
            if depth >= max_depth:
                # For max_depth=1, only root (depth=0). For max_depth=2, root and one level below (depth=0,1).
                if depth > 0:
                    continue
        dirs, files = filter_ignored(root, dirs, files)
        yield root, dirs, files
