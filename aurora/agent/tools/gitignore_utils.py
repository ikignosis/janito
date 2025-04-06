import os
import fnmatch


def load_gitignore_patterns(gitignore_path='.gitignore'):
    patterns = []
    if not os.path.exists(gitignore_path):
        return patterns
    with open(gitignore_path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            patterns.append(line)
    return patterns


def is_ignored(path, patterns):
    for pattern in patterns:
        # Handle directory ignore
        if pattern.endswith('/'):
            if os.path.isdir(path) and fnmatch.fnmatch(path + '/', pattern):
                return True
            if path.startswith(pattern):
                return True
        # Handle file ignore
        if fnmatch.fnmatch(path, pattern):
            return True
    return False


def filter_ignored(root, dirs, files, patterns):
    # Modify dirs in-place to skip ignored directories
    dirs[:] = [d for d in dirs if not is_ignored(os.path.join(root, d), patterns)]
    # Filter files
    files = [f for f in files if not is_ignored(os.path.join(root, f), patterns)]
    return dirs, files
