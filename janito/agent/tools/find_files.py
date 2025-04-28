from janito.agent.tool_base import ToolBase
from janito.agent.tool_registry import register_tool
from janito.agent.tools.tools_utils import pluralize, display_path
from janito.agent.tools.dir_walk_utils import walk_dir_with_gitignore
from janito.i18n import tr
import fnmatch
import os


@register_tool(name="find_files")
class FindFilesTool(ToolBase):
    """
    Find files in one or more directories matching a pattern. Respects .gitignore.
    Args:
        paths (str): String of one or more paths (space-separated) to search in. Each path can be a directory.
        pattern (str): File pattern(s) to match. Multiple patterns can be separated by spaces. Uses Unix shell-style wildcards (fnmatch), e.g. '*.py', 'data_??.csv', '[a-z]*.txt'.
        max_depth (int, optional): Maximum directory depth to search. If 0 (default), search is recursive with no depth limit. If >0, limits recursion to that depth. Setting max_depth=1 disables recursion (only top-level directory).
        max_results (int, optional): Maximum number of results to return. 0 means no limit (default).
    Returns:
        str: Newline-separated list of matching file paths. Example:
            "/path/to/file1.py\n/path/to/file2.py"
            "Warning: Empty file pattern provided. Operation skipped."
            If max_results is reached, appends a note to the output.
    """

    def run(self, paths: str, pattern: str, max_depth: int = 0) -> str:
        if not pattern:
            self.report_warning(
                tr("⚠️  Warning: Empty file pattern provided. Operation skipped.")
            )
            return tr("Warning: Empty file pattern provided. Operation skipped.")
        output = set()
        patterns = pattern.split()
        for directory in paths.split():
            disp_path = display_path(directory)
            depth_msg = (
                tr(" (max depth: {max_depth})", max_depth=max_depth)
                if max_depth > 0
                else ""
            )
            self.report_info(
                tr(
                    "🔍 Searching for files '{pattern}' in '{disp_path}'{depth_msg} ...",
                    pattern=pattern,
                    disp_path=disp_path,
                    depth_msg=depth_msg,
                )
            )
            for root, dirs, files in walk_dir_with_gitignore(
                directory, max_depth=max_depth
            ):
                for pat in patterns:
                    for filename in fnmatch.filter(files, pat):
                        output.add(os.path.join(root, filename))
        self.report_success(
            tr(
                " ✅ {count} {file_word} found",
                count=len(output),
                file_word=pluralize("file", len(output)),
            )
        )
        # If searching in '.', strip leading './' from results
        if paths.strip() == ".":
            output = {
                p[2:] if (p.startswith("./") or p.startswith(".\\")) else p
                for p in output
            }
        result = "\n".join(sorted(output))
        return result
