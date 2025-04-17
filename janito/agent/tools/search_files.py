import os
import re
import fnmatch
from janito.agent.tool_handler import ToolHandler
from janito.agent.tools.rich_utils import print_info, print_success, print_error, format_path, format_number
from janito.agent.tools.gitignore_utils import load_gitignore_patterns, filter_ignored
from janito.agent.tools.utils import expand_path, display_path

@ToolHandler.register_tool
def search_files(
    directory: str,
    pattern: str
) -> str:
    """
    Search for a text pattern in all files within a directory and return matching lines and their content.

    Args:
        directory (str): The directory to search in.
        pattern (str): The text pattern to search for.
    Returns:
        str: Each match as 'filepath:lineno:linecontent', one per line.
    """
    directory = expand_path(directory)
    print_info(f"🔎 search_files | Path: {directory} | pattern: '{pattern}'")
    results = []
    ignore_patterns = load_gitignore_patterns()
    try:
        regex = re.compile(pattern, re.IGNORECASE)
    except re.error:
        regex = None

    files_to_search = []
    if os.path.isfile(directory):
        files_to_search = [directory]
    else:
        for root, dirs, files in os.walk(directory):
            dirs, files = filter_ignored(root, dirs, files, ignore_patterns)
            for file in files:
                filepath = os.path.join(root, file)
                files_to_search.append(filepath)

    for filepath in files_to_search:
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            disp_path = display_path(os.path.relpath(filepath, os.getcwd()), filepath)
            for lineno, line in enumerate(f, start=1):
                if regex:
                    if regex.search(line):
                        results.append(f"{disp_path}:{lineno}:{line.rstrip()}")
                else:
                    if pattern.lower() in line.lower():
                        results.append(f"{disp_path}:{lineno}:{line.rstrip()}")

    print_success(f"✅ Found {format_number(len(results))} matches")
    return "\n".join(results)
