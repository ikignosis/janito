import os
import re
import fnmatch
from aurora.agent.tool_handler import ToolHandler
from aurora.agent.tools.rich_utils import print_info, print_success, print_error, format_path, format_number
from aurora.agent.tools.gitignore_utils import load_gitignore_patterns, filter_ignored

@ToolHandler.register_tool
def search_text(directory: str, file_pattern: str, text_pattern: str, case_sensitive: bool = False, max_matches: int = 1000):
    """
    directory: Root directory to search.
    file_pattern: Glob pattern for filenames (e.g., '*.py').
    text_pattern: Regex pattern to search within files.
    case_sensitive: Whether the search is case sensitive.
    max_matches: Maximum number of matches to return.

    Returns a string with matches, each in 'filepath:line_number:matched_line' format, separated by newlines.
    """
    print_info(f"🔎 Searching for pattern '{text_pattern}' in files under '{format_path(directory)}' matching '{file_pattern}' ...")
    flags = 0 if case_sensitive else re.IGNORECASE
    regex = re.compile(text_pattern, flags)
    results = []
    ignore_patterns = load_gitignore_patterns()

    try:
        for root, dirs, files in os.walk(directory):
            dirs, files = filter_ignored(root, dirs, files, ignore_patterns)
            for filename in fnmatch.filter(files, file_pattern):
                filepath = os.path.join(root, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
                        for lineno, line in enumerate(f, start=1):
                            if regex.search(line):
                                results.append(f"{filepath}:{lineno}:{line.rstrip()}")
                                if len(results) >= max_matches:
                                    print_success(f"✅ Found {format_number(len(results))} matches (limit reached)")
                                    return "\n".join(results)
                except Exception as e:
                    print_error(f"❌ Error reading file '{filepath}': {e}")
                    continue  # Ignore unreadable files
        print_success(f"✅ Found {format_number(len(results))} matches")
    except Exception as e:
        print_error(f"❌ Error during search: {e}")

    return "\n".join(results)
