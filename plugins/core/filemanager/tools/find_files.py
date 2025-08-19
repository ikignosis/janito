from janito.tools.tool_base import ToolBase, ToolPermissions
from janito.report_events import ReportAction
from janito.tools.adapters.local.adapter import register_local_tool
from janito.tools.tool_utils import pluralize, display_path
from janito.dir_walk_utils import walk_dir_with_gitignore
from janito.i18n import tr
import fnmatch
import os
from janito.tools.path_utils import expand_path
from janito.tools.loop_protection_decorator import protect_against_loops


@register_local_tool
class FindFilesTool(ToolBase):
    """
    Find files or directories in one or more directories matching a pattern. Respects .gitignore.

    If a path is an existing file, it is checked against the provided pattern(s) and included in the results if it matches. This allows find_files to be used to look for a specific set of filenames in a single call, as well as searching directories.

    Args:
        paths (str): String of one or more paths (space-separated) to search in. Each path can be a directory or a file.
        pattern (str): File pattern(s) to match. Multiple patterns can be separated by spaces. Uses Unix shell-style wildcards (fnmatch), e.g. '*.py', 'data_??.csv', '[a-z]*.txt'.
            - If the pattern ends with '/' or '\', only matching directory names (with trailing slash) are returned, not the files within those directories. For example, pattern '*/' will return only directories at the specified depth.
        max_depth (int, optional): Maximum directory depth to search. If None, unlimited recursion. If 0, only the top-level directory. If 1, only the root directory (matches 'find . -maxdepth 1').
        include_gitignored (bool, optional): If True, includes files/directories ignored by .gitignore. Defaults to False.
    Returns:
        str: Newline-separated list of matching file paths. Example:
            "/path/to/file1.py\n/path/to/file2.py"
            "Warning: Empty file pattern provided. Operation skipped."
    """

    permissions = ToolPermissions(read=True)
    tool_name = "find_files"

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

    def _handle_path(self, directory, patterns):
        dir_output = set()
        filename = os.path.basename(directory)
        for pat in patterns:
            # Only match files, not directories, for file paths
            if not (pat.endswith("/") or pat.endswith("\\")):
                if fnmatch.fnmatch(filename, pat):
                    dir_output.add(directory)
                    break
        return dir_output

    def _handle_directory_path(
        self, directory, patterns, max_depth, include_gitignored
    ):
        dir_output = set()
        for root, dirs, files in walk_dir_with_gitignore(
            directory,
            max_depth=max_depth,
            include_gitignored=include_gitignored,
        ):
            for pat in patterns:
                if pat.endswith("/") or pat.endswith("\\"):
                    dir_output.update(self._match_directories(root, dirs, pat))
                else:
                    dir_output.update(self._match_files(root, files, pat))
                    dir_output.update(self._match_dirs_without_slash(root, dirs, pat))
        return dir_output

    def _report_search(self, pattern, disp_path, depth_msg):
        self.report_action(
            tr(
                "🔍 Search for files '{pattern}' in '{disp_path}'{depth_msg} ...",
                pattern=pattern,
                disp_path=disp_path,
                depth_msg=depth_msg,
            ),
            ReportAction.READ,
        )

    def _report_success(self, count):
        self.report_success(
            tr(
                " ✅ {count} {file_word}",
                count=count,
                file_word=pluralize("file", count),
            ),
            ReportAction.READ,
        )

    def _format_output(self, directory, dir_output):
        if directory.strip() == ".":
            dir_output = {
                p[2:] if (p.startswith("./") or p.startswith(".\\")) else p
                for p in dir_output
            }
        return sorted(dir_output)

    @protect_against_loops(max_calls=5, time_window=10.0, key_field="paths")
    def run(
        self,
        paths: str,
        pattern: str,
        max_depth: int = None,
        include_gitignored: bool = False,
    ) -> str:
        if not pattern:
            self.report_warning(tr("ℹ️ Empty file pattern provided."), ReportAction.READ)
            return tr("Warning: Empty file pattern provided. Operation skipped.")
        patterns = pattern.split()
        results = []
        for directory in [expand_path(p) for p in paths.split()]:
            disp_path = display_path(directory)
            depth_msg = (
                tr(" (max depth: {max_depth})", max_depth=max_depth)
                if max_depth is not None and max_depth > 0
                else ""
            )
            self._report_search(pattern, disp_path, depth_msg)
            dir_output = set()
            if os.path.isfile(directory):
                dir_output = self._handle_path(directory, patterns)
            elif os.path.isdir(directory):
                dir_output = self._handle_directory_path(
                    directory, patterns, max_depth, include_gitignored
                )
            self._report_success(len(dir_output))
            results.extend(self._format_output(directory, dir_output))
        result = "\n".join(results)
        return result
