import os
import fnmatch
from janito.agent.tool_handler import ToolHandler
from janito.agent.tools.rich_utils import print_info, print_success, print_error
from janito.agent.tools.utils import expand_path, display_path
from janito.agent.tools.tool_base import ToolBase

# Converted find_files into a ToolBase subclass
class FindFilesTool(ToolBase):
    """Find files in a directory matching a pattern.

    Args:
        directory (str): The directory to search in.
        pattern (str): The filename pattern to match (e.g., '*.txt').
        recursive (bool): Whether to search subdirectories.
        max_results (int): Maximum number of results to return.

    Returns:
        str: Newline-separated list of matching file paths, with summary and warnings if truncated.
    """
    def call(self, directory: str, pattern: str, recursive: bool=False, max_results: int=100) -> str:
        original_directory = directory
        directory = expand_path(directory)
        disp_dir = display_path(original_directory, directory)
        print_info(f"🔍 Searching for files in: '{disp_dir}' | Pattern: '{pattern}' | Recursive: {recursive} | Max: {max_results}")
        if not os.path.isdir(directory):
            print_error(f"❌ Not a directory: {disp_dir}")
            return ""
        if not isinstance(max_results, int) or max_results <= 0:
            print_error(f"❌ Invalid max_results value: {max_results}")
            return ""
        matches = []
        try:
            if recursive:
                for root, dirs, files in os.walk(directory):
                    for name in files:
                        if fnmatch.fnmatch(name, pattern):
                            matches.append(os.path.join(root, name))
                            if len(matches) >= max_results:
                                break
                    if len(matches) >= max_results:
                        break
            else:
                for name in os.listdir(directory):
                    full_path = os.path.join(directory, name)
                    if os.path.isfile(full_path) and fnmatch.fnmatch(name, pattern):
                        matches.append(full_path)
                        if len(matches) >= max_results:
                            break
        except Exception as e:
            print_error(f"❌ Error during file search: {e}")
            return ""
        print_success(f"✅ Found {len(matches)} file(s)")
        result = f"Total files found: {len(matches)}\n"
        result += "\n".join([display_path(original_directory + m[len(directory):] if m.startswith(directory) else m, m) for m in matches])
        if len(matches) == max_results:
            result += "\n# WARNING: Results truncated at max_results. There may be more matching files."
        return result

ToolHandler.register_tool(FindFilesTool, name="find_files")
