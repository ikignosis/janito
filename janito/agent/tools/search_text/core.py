from janito.agent.tool_base import ToolBase
from janito.agent.tools_utils.action_type import ActionType
from janito.agent.tool_registry import register_tool
from janito.agent.tools_utils.utils import pluralize, display_path
from janito.i18n import tr
import os
from .pattern_utils import prepare_pattern, format_result, summarize_total
from .match_lines import read_file_lines
from .traverse_directory import traverse_directory


@register_tool(name="search_text")
class SearchTextTool(ToolBase):
    """
    Search for a text pattern (regex or plain string) in all files within one or more directories or file paths and return matching lines or counts. Respects .gitignore.
    Args:
        paths (str): String of one or more paths (space-separated) to search in. Each path can be a directory or a file.
        pattern (str): Regex pattern or plain text substring to search for in files. Must not be empty. Tries regex first, falls back to substring if regex is invalid.
        is_regex (bool): If True, treat pattern as a regular expression. If False, treat as plain text (default).
        max_depth (int, optional): Maximum directory depth to search. If 0 (default), search is recursive with no depth limit. If >0, limits recursion to that depth. Setting max_depth=1 disables recursion (only top-level directory). Ignored for file paths.
        max_results (int, optional): Maximum number of results to return. Defaults to 100. 0 means no limit.
        count_only (bool): If True, return only the count of matches per file and total, not the matching lines. Default is False.
    Returns:
        str: If count_only is False, matching lines from files as a newline-separated string, each formatted as 'filepath:lineno: line'.
             If count_only is True, returns per-file and total match counts.
        If max_results is reached, appends a note to the output.
    """

    def _handle_file(
        self,
        search_path,
        pattern,
        regex,
        use_regex,
        max_results,
        total_results,
        count_only,
    ):
        if count_only:
            match_count, dir_limit_reached, _ = read_file_lines(
                search_path,
                pattern,
                regex,
                use_regex,
                True,
                max_results,
                total_results,
            )
            per_file_counts = [(search_path, match_count)] if match_count > 0 else []
            return [], dir_limit_reached, per_file_counts
        else:
            dir_output, dir_limit_reached, match_count_list = read_file_lines(
                search_path,
                pattern,
                regex,
                use_regex,
                False,
                max_results,
                total_results,
            )
            per_file_counts = (
                [(search_path, len(match_count_list))]
                if match_count_list and len(match_count_list) > 0
                else []
            )
            return dir_output, dir_limit_reached, per_file_counts

    def _handle_path(
        self,
        search_path,
        pattern,
        regex,
        use_regex,
        max_depth,
        max_results,
        total_results,
        count_only,
    ):
        info_str = tr(
            "\U0001f50d Search {search_type} '{pattern}' in '{disp_path}'",
            search_type=("regex" if use_regex else "text"),
            pattern=pattern,
            disp_path=display_path(search_path),
        )
        if max_depth > 0:
            info_str += tr(" [max_depth={max_depth}]", max_depth=max_depth)
        if count_only:
            info_str += " [count]"
        self.report_info(ActionType.READ, info_str)
        if os.path.isfile(search_path):
            dir_output, dir_limit_reached, per_file_counts = self._handle_file(
                search_path,
                pattern,
                regex,
                use_regex,
                max_results,
                total_results,
                count_only,
            )
        else:
            if count_only:
                per_file_counts, dir_limit_reached, _ = traverse_directory(
                    search_path,
                    pattern,
                    regex,
                    use_regex,
                    max_depth,
                    max_results,
                    total_results,
                    True,
                )
                dir_output = []
            else:
                dir_output, dir_limit_reached, per_file_counts = traverse_directory(
                    search_path,
                    pattern,
                    regex,
                    use_regex,
                    max_depth,
                    max_results,
                    total_results,
                    False,
                )
        count = sum(count for _, count in per_file_counts)
        file_word = pluralize("match", count)
        self.report_success(
            tr(
                " ✅ {count} {file_word}{max_flag}",
                count=count,
                file_word=file_word,
                max_flag=" (max)" if dir_limit_reached else "",
            )
        )
        return info_str, dir_output, dir_limit_reached, per_file_counts

    def run(
        self,
        paths: str,
        pattern: str,
        is_regex: bool = False,
        max_depth: int = 0,
        max_results: int = 100,
        count_only: bool = False,
    ) -> str:
        regex, use_regex, error_msg = prepare_pattern(
            pattern, is_regex, self.report_error, self.report_warning
        )
        if error_msg:
            return error_msg
        paths_list = paths.split()
        results = []
        all_per_file_counts = []
        for search_path in paths_list:
            info_str, dir_output, dir_limit_reached, per_file_counts = (
                self._handle_path(
                    search_path,
                    pattern,
                    regex,
                    use_regex,
                    max_depth,
                    max_results,
                    0,
                    count_only,
                )
            )
            if count_only:
                all_per_file_counts.extend(per_file_counts)
            result_str = format_result(
                pattern,
                use_regex,
                dir_output,
                dir_limit_reached,
                count_only,
                per_file_counts,
            )
            results.append(info_str + "\n" + result_str)
            if dir_limit_reached:
                break
        if count_only:
            results.append(summarize_total(all_per_file_counts))
        return "\n\n".join(results)
