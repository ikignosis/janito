from janito.agent.tool_base import ToolBase
from janito.agent.tool_registry import register_tool
from janito.agent.tools_utils.utils import pluralize
from janito.i18n import tr
import os
import re
from janito.agent.tools_utils.gitignore_utils import filter_ignored


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


@register_tool(name="search_text")
class SearchTextTool(ToolBase):
    """
    Search for a text pattern (regex or plain string) in all files within one or more directories or file paths and return matching lines. Respects .gitignore.

    Args:
        paths (str): String of one or more paths (space-separated) to search in. Each path can be a directory or a file.
        pattern (str): Regex pattern or plain text substring to search for in files. Must not be empty. Tries regex first, falls back to substring if regex is invalid.
            Note: When using regex mode, special characters (such as [, ], ., *, etc.) must be escaped if you want to match them literally (e.g., use '\\[DEBUG\\]' to match the literal string '[DEBUG]').
        is_regex (bool): If True, treat pattern as regex. If False, treat as plain text. Defaults to False.
        max_depth (int, optional): Maximum directory depth to search. If 0 (default), search is recursive with no depth limit. If >0, limits recursion to that depth. Setting max_depth=1 disables recursion (only top-level directory). Ignored for file paths.
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
            self.report_error(
                tr("Error: Empty search pattern provided. Operation aborted.")
            )
            return tr("Error: Empty search pattern provided. Operation aborted.")
        regex = None
        use_regex = False
        if is_regex:
            try:
                regex = re.compile(pattern)
                use_regex = True
            except re.error as e:
                self.report_warning(tr("⚠️ Invalid regex pattern."))
                return tr(
                    "Warning: Invalid regex pattern: {error}. No results.", error=e
                )
        else:
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
        for search_path in paths_list:
            from janito.agent.tools_utils.utils import display_path

            info_str = tr(
                "🔍 Searching for {search_type} '{pattern}' in '{disp_path}'",
                search_type=("text-regex" if use_regex else "text"),
                pattern=pattern,
                disp_path=display_path(search_path),
            )
            if max_depth > 0:
                info_str += tr(" [max_depth={max_depth}]", max_depth=max_depth)
            self.report_info(info_str)
            dir_output = []
            dir_limit_reached = False
            if os.path.isfile(search_path):
                # Handle single file
                path = search_path
                if not is_binary_file(path):
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
                                    break
                    except Exception:
                        pass
                output.extend(dir_output)
                total_results += len(dir_output)
                if dir_limit_reached:
                    limit_reached = True
                    break
                continue
            # Directory logic as before
            if max_depth == 1:
                walk_result = next(os.walk(search_path), None)
                if walk_result is None:
                    walker = [(search_path, [], [])]
                else:
                    _, dirs, files = walk_result
                    dirs, files = filter_ignored(search_path, dirs, files)
                    walker = [(search_path, dirs, files)]
            else:
                walker = os.walk(search_path)
            stop_search = False
            for root, dirs, files in walker:
                if stop_search:
                    break
                rel_path = os.path.relpath(root, search_path)
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
        header = tr(
            "[search_text] Pattern: '{pattern}' | Regex: {use_regex} | Results: {count}",
            pattern=pattern,
            use_regex=use_regex,
            count=len(output),
        )
        result = header + "\n" + "\n".join(output)
        if limit_reached:
            result += tr("\n[Note: max_results limit reached, output truncated.]")
        self.report_success(
            tr(
                " ✅ {count} {line_word}{limit}",
                count=len(output),
                line_word=pluralize("line", len(output)),
                limit=(" (limit reached)" if limit_reached else ""),
            )
        )
        return result
