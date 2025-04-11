import os
import fnmatch
from janito.agent.tool_handler import ToolHandler
from janito.agent.tools.rich_utils import print_info, print_success, print_error, format_path, format_number
from janito.agent.tools.gitignore_utils import load_gitignore_patterns, filter_ignored

@ToolHandler.register_tool
def find_files(directory: str, pattern: str = "*") -> str:
    """
    Recursively find files matching a pattern within a directory, skipping ignored files/dirs.

    directory: The root directory to start searching from.
    pattern: Glob pattern to match filenames (default: '*').
    """
    print_info(f"🔍 Searching for files in '{format_path(directory)}' matching pattern '{pattern}' ... ")

    # Check if pattern is an exact relative path to a file
    full_path = os.path.join(directory, pattern)
    if os.path.isfile(full_path):
        print_success("✅ Found 1 file (exact match)")
        return full_path

    matches = []
    ignore_patterns = load_gitignore_patterns()
    try:
        for root, dirs, files in os.walk(directory):
            dirs, files = filter_ignored(root, dirs, files, ignore_patterns)
            for filename in fnmatch.filter(files, pattern):
                matches.append(os.path.join(root, filename))
        print_success(f"✅ Found {format_number(len(matches))} files")
        if matches:
            return "\n".join(matches)
        else:
            return "No matching files found."
    except Exception as e:
        print_error(f"❌ Error: {e}")
        return f"❌ Failed to search files in '{directory}': {e}"
