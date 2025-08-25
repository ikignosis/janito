import re
from janito.gitignore_utils import GitignoreFilter
import os


def is_binary_file(path, blocksize=1024):
    try:
        with open(path, "rb") as f:
            chunk = f.read(blocksize)
            if b"\0" in chunk:
                return True
            text_characters = bytearray(
                {7, 8, 9, 10, 12, 13, 27} | set(range(0x20, 0x100))
            )
            nontext = chunk.translate(None, text_characters)
            if len(nontext) / max(1, len(chunk)) > 0.3:
                return True
    except Exception:
        return True
    return False


def match_line(line, query, regex, use_regex, case_sensitive):
    if use_regex:
        return regex and regex.search(line)
    if not case_sensitive:
        return query.lower() in line.lower()
    return query in line


def should_limit(max_results, total_results, match_count, count_only, dir_output):
    if max_results > 0:
        current_count = total_results + (match_count if count_only else len(dir_output))
        return current_count >= max_results
    return False


def read_file_lines(
    path,
    query,
    regex,
    use_regex,
    case_sensitive,
    count_only,
    max_results,
    total_results,
):
    dir_output = []
    dir_limit_reached = False
    match_count = 0
    if not is_binary_file(path):
        try:
            open_kwargs = {"mode": "r", "encoding": "utf-8"}
            with open(path, **open_kwargs) as f:
                for lineno, line in enumerate(f, 1):
                    if match_line(line, query, regex, use_regex, case_sensitive):
                        match_count += 1
                        if not count_only:
                            dir_output.append(f"{path}:{lineno}: {line.rstrip()}")
                    if should_limit(
                        max_results, total_results, match_count, count_only, dir_output
                    ):
                        dir_limit_reached = True
                        break
        except Exception:
            pass
    return match_count, dir_limit_reached, dir_output
