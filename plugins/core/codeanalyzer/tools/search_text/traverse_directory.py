import os
from janito.gitignore_utils import GitignoreFilter
from .match_lines import match_line, should_limit, read_file_lines


def walk_directory(search_path, max_depth):
    if max_depth == 1:
        walk_result = next(os.walk(search_path), None)
        if walk_result is None:
            return [(search_path, [], [])]
        else:
            return [walk_result]
    else:
        return os.walk(search_path)


def filter_dirs(dirs, root, gitignore_filter):
    # Always exclude directories named .git, regardless of gitignore
    return [
        d
        for d in dirs
        if d != ".git" and not gitignore_filter.is_ignored(os.path.join(root, d))
    ]


def process_file_count_only(
    path,
    per_file_counts,
    query,
    regex,
    use_regex,
    case_sensitive,
    max_results,
    total_results,
):
    match_count, file_limit_reached, _ = read_file_lines(
        path,
        query,
        regex,
        use_regex,
        case_sensitive,
        True,
        max_results,
        total_results + sum(count for _, count in per_file_counts),
    )
    if match_count > 0:
        per_file_counts.append((path, match_count))
    return file_limit_reached


def process_file_collect(
    path,
    dir_output,
    per_file_counts,
    query,
    regex,
    use_regex,
    case_sensitive,
    max_results,
    total_results,
):
    actual_match_count, file_limit_reached, file_lines_output = read_file_lines(
        path,
        query,
        regex,
        use_regex,
        case_sensitive,
        False,
        max_results,
        total_results + len(dir_output),
    )
    dir_output.extend(file_lines_output)
    if actual_match_count > 0:
        per_file_counts.append((path, actual_match_count))
    return file_limit_reached


def should_limit_depth(root, search_path, max_depth, dirs):
    if max_depth > 0:
        rel_root = os.path.relpath(root, search_path)
        if rel_root != ".":
            depth = rel_root.count(os.sep) + 1
            if depth >= max_depth:
                del dirs[:]


def traverse_directory(
    search_path,
    query,
    regex,
    use_regex,
    case_sensitive,
    max_depth,
    max_results,
    total_results,
    count_only,
):
    dir_output = []
    dir_limit_reached = False
    per_file_counts = []
    walker = walk_directory(search_path, max_depth)
    gitignore_filter = GitignoreFilter(search_path)

    for root, dirs, files in walker:
        dirs[:] = filter_dirs(dirs, root, gitignore_filter)
        for file in files:
            path = os.path.join(root, file)
            if gitignore_filter.is_ignored(path):
                continue
            if count_only:
                file_limit_reached = process_file_count_only(
                    path,
                    per_file_counts,
                    query,
                    regex,
                    use_regex,
                    case_sensitive,
                    max_results,
                    total_results,
                )
                if file_limit_reached:
                    dir_limit_reached = True
                    break
            else:
                file_limit_reached = process_file_collect(
                    path,
                    dir_output,
                    per_file_counts,
                    query,
                    regex,
                    use_regex,
                    case_sensitive,
                    max_results,
                    total_results,
                )
                if file_limit_reached:
                    dir_limit_reached = True
                    break
        if dir_limit_reached:
            break
        should_limit_depth(root, search_path, max_depth, dirs)
    if count_only:
        return per_file_counts, dir_limit_reached, []
    else:
        return dir_output, dir_limit_reached, per_file_counts
