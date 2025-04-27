from janito.agent.tool_base import ToolBase
from janito.agent.tool_registry import register_tool
from janito.agent.tools.tools_utils import pluralize

import os
import re
from janito.agent.tools.gitignore_utils import filter_ignored


def is_binary_file(path, blocksize=1024):
    try:
        with open(path, "rb") as f:
            chunk = f.read(blocksize)
            if b"\0" in chunk:
                return True
            # Heuristic: if more than 30% of the bytes are non-text, treat as binary
            text_characters = bytearray(
                {7, 8, 9, 10, 12, 13, 27} | set(range(0x20, 0x100))
            )
            nontext = chunk.translate(None, text_characters)
            if len(nontext) / max(1, len(chunk)) > 0.3:
                return True
    except Exception:
        return True  # treat unreadable files as binary
    return False


@register_tool(name="search_text")
class SearchTextTool(ToolBase):
    """
    Search for a text pattern (regex or plain string) in all files within one or more directories and return matching lines. Respects .gitignore.

    Args:
        paths (str): String of one or more paths (space-separated) to search in. Each path can be a directory or a filename.
        pattern (str): Regex pattern or plain text substring to search for in files. Tries regex first, falls back to substring if regex is invalid.
        is_regex (bool): If True, treat pattern as regex. If False, treat as plain text. Defaults to False.
        max_depth (int, optional): Maximum directory depth to search. If 0 (default), search is recursive with no depth limit. If >0, limits recursion to that depth. Setting max_depth=1 disables recursion (only top-level directory).
        max_results (int): Maximum number of results to return. 0 means no limit (default).
        ignore_utf8_errors (bool): If True, ignore utf-8 decode errors. Defaults to True.
    Returns:
        str: Matching lines from files as a newline-separated string, each formatted as 'filepath:lineno: line'.
        If max_results is reached, appends a note to the output.
    """

    def run(
        self,
        paths: str,
        pattern: str,
        is_regex: bool = False,
        max_depth: int = 0,
        max_results: int = 0,
        ignore_utf8_errors: bool = True,
    ) -> str:
        if not pattern:
            self.report_warning(
                "\u26a0\ufe0f Warning: Empty search pattern provided. Operation skipped."
            )
            return "Warning: Empty search pattern provided. Operation skipped."
        # Try compiling regex if requested
        regex = None
        use_regex = False
        if is_regex:
            try:
                regex = re.compile(pattern)
                use_regex = True
            except re.error as e:
                self.report_warning(
                    f"Invalid regex pattern: {e}. Falling back to no results."
                )
                return f"Warning: Invalid regex pattern: {e}. No results."
        else:
            # Legacy: try regex first, fallback to substring
            try:
                regex = re.compile(pattern)
                use_regex = True
            except re.error:
                regex = None
                use_regex = False

        output = []
        limit_reached = False
        total_results = 0
        paths_list = paths.split()
        for directory in paths_list:
            info_str = f"\U0001f50d Searching for {'text-regex' if use_regex else 'text'} '{pattern}' in '{directory}'"
            if max_depth > 0:
                info_str += f" [max_depth={max_depth}]"
            self.report_info(info_str)
            dir_output = []
            dir_limit_reached = False
            if max_depth == 1:
                walk_result = next(os.walk(directory), None)
                if walk_result is None:
                    walker = [(directory, [], [])]
                else:
                    _, dirs, files = walk_result
                    dirs, files = filter_ignored(directory, dirs, files)
                    walker = [(directory, dirs, files)]
            else:
                walker = os.walk(directory)
            stop_search = False
            for root, dirs, files in walker:
                if stop_search:
                    break
                rel_path = os.path.relpath(root, directory)
                depth = 0 if rel_path == "." else rel_path.count(os.sep) + 1
                if max_depth == 1 and depth > 0:
                    break
                if max_depth > 0 and depth > max_depth:
                    continue
                dirs, files = filter_ignored(root, dirs, files)
                for filename in files:
                    if stop_search:
                        break
                    path = os.path.join(root, filename)
                    if is_binary_file(path):
                        continue
                    try:
                        open_kwargs = {"mode": "r", "encoding": "utf-8"}
                        if ignore_utf8_errors:
                            open_kwargs["errors"] = "ignore"
                        with open(path, **open_kwargs) as f:
                            for lineno, line in enumerate(f, 1):
                                if use_regex:
                                    if regex.search(line):
                                        dir_output.append(
                                            f"{path}:{lineno}: {line.strip()}"
                                        )
                                else:
                                    if pattern in line:
                                        dir_output.append(
                                            f"{path}:{lineno}: {line.strip()}"
                                        )
                                if (
                                    max_results > 0
                                    and (total_results + len(dir_output)) >= max_results
                                ):
                                    dir_limit_reached = True
                                    stop_search = True
                                    break
                    except Exception:
                        continue
            output.extend(dir_output)
            total_results += len(dir_output)
            if dir_limit_reached:
                limit_reached = True
                break
        header = f"[search_text] Pattern: '{pattern}' | Regex: {use_regex} | Results: {len(output)}"
        result = header + "\n" + "\n".join(output)
        if limit_reached:
            result += "\n[Note: max_results limit reached, output truncated.]"
        self.report_success(
            f" \u2705 {len(output)} {pluralize('line', len(output))} found"
            + (" (limit reached)" if limit_reached else "")
        )
        return result
