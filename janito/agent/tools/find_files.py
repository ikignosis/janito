from janito.agent.tool_base import ToolBase
from janito.agent.tools_utils.action_type import ActionType
from janito.agent.tool_registry import register_tool
from janito.agent.tools_utils.utils import pluralize, display_path
from janito.agent.tools_utils.dir_walk_utils import walk_dir_with_gitignore
from janito.i18n import tr
import fnmatch
import os


@register_tool(name="find_files")
class FindFilesTool(ToolBase):
    """
    Find files or directories in one or more directories matching a pattern. Respects .gitignore.
    Args:
        paths (str): String of one or more paths (space-separated) to search in. Each path can be a directory.
        pattern (str): File pattern(s) to match. Multiple patterns can be separated by spaces. Uses Unix shell-style wildcards (fnmatch), e.g. '*.py', 'data_??.csv', '[a-z]*.txt'.
            - If the pattern ends with '/' or '\\', only matching directory names (with trailing slash) are returned, not the files within those directories. For example, pattern '*/' will return only directories at the specified depth.
        max_depth (int, optional): Maximum directory depth to search. If None, unlimited recursion. If 0, only the top-level directory. If 1, only the root directory (matches 'find . -maxdepth 1').
        max_results (int, optional): Maximum number of results to return. 0 means no limit (default).
    Returns:
        str: Newline-separated list of matching file paths. Example:
            "/path/to/file1.py\n/path/to/file2.py"
            "Warning: Empty file pattern provided. Operation skipped."
            If max_results is reached, appends a note to the output.
    """

    def _match_directories(self, root, dirs, pat):
        dir_output = set()
        dir_pat = pat.rstrip("/\\")
        for d in dirs:
            if fnmatch.fnmatch(d, dir_pat):
                dir_output.add(os.path.join(root, d) + os.sep)
        return dir_output

    def _match_files(self, root, files, pat):
        file_output = set()
        for filename in fnmatch.filter(files, pat):
            file_output.add(os.path.join(root, filename))
        return file_output

    def _match_dirs_without_slash(self, root, dirs, pat):
        dir_output = set()
        for d in fnmatch.filter(dirs, pat):
            dir_output.add(os.path.join(root, d))
        return dir_output

    def run(self, paths: str, pattern: str, max_depth: int = None) -> str:
        if not pattern:
            self.report_warning(tr("ℹ️ Empty file pattern provided."))
            return tr("Warning: Empty file pattern provided. Operation skipped.")
        patterns = pattern.split()
        results = []
        for directory in paths.split():
            disp_path = display_path(directory)
            depth_msg = (
                tr(" (max depth: {max_depth})", max_depth=max_depth)
                if max_depth is not None and max_depth > 0
                else ""
            )
            self.report_info(
                ActionType.READ,
                tr(
                    "🔍 Search for files '{pattern}' in '{disp_path}'{depth_msg} ...",
                    pattern=pattern,
                    disp_path=disp_path,
                    depth_msg=depth_msg,
                ),
            )
            dir_output = set()
            for root, dirs, files in walk_dir_with_gitignore(
                directory, max_depth=max_depth
            ):
                for pat in patterns:
                    if pat.endswith("/") or pat.endswith("\\"):
                        dir_output.update(self._match_directories(root, dirs, pat))
                    else:
                        dir_output.update(self._match_files(root, files, pat))
                        dir_output.update(
                            self._match_dirs_without_slash(root, dirs, pat)
                        )
            self.report_success(
                tr(
                    " ✅ {count} {file_word}",
                    count=len(dir_output),
                    file_word=pluralize("file", len(dir_output)),
                )
            )
            if directory.strip() == ".":
                dir_output = {
                    p[2:] if (p.startswith("./") or p.startswith(".\\")) else p
                    for p in dir_output
                }
            results.extend(sorted(dir_output))
        result = "\n".join(results)
        return result
