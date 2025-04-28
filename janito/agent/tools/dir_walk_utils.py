import os
from janito.agent.tools.gitignore_utils import filter_ignored


def walk_dir_with_gitignore(root_dir, max_depth=0):
    """
    Walks the directory tree starting at root_dir, yielding (root, dirs, files) tuples,
    with .gitignore rules applied. If max_depth > 0, limits recursion to that depth.
    """
    for root, dirs, files in os.walk(root_dir):
        rel_path = os.path.relpath(root, root_dir)
        depth = 0 if rel_path == "." else rel_path.count(os.sep) + 1
        if max_depth > 0 and depth > max_depth:
            continue
        dirs, files = filter_ignored(root, dirs, files)
        yield root, dirs, files
