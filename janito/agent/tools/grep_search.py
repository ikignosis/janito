import os
import re
import fnmatch
from janito.agent.tool_handler import ToolHandler
from janito.agent.tools.rich_utils import print_info, print_success, print_error, format_path, format_number
from janito.agent.tools.gitignore_utils import load_gitignore_patterns, filter_ignored

@ToolHandler.register_tool
def grep_search(
    Query: str,
    SearchPath: str,
    CaseInsensitive: bool = False,
    Includes: list = None,
    MatchPerLine: bool = True
) -> str:
    """
    Search for pattern matches within files or directories (like egrep, supporting regular expressions).
    Parameters:
      - Query (string, required): The search term or pattern to look for.
      - SearchPath (string, required): The directory or file to search in.
      - CaseInsensitive (bool, optional): Set to true to perform a case-insensitive search (default: false).
      - Includes (list of string, optional): File patterns or paths to include (default: all files).
      - MatchPerLine (bool, optional): If true, returns each matching line with line numbers and snippets; if false, returns only file names containing matches (default: true).
    """
    if Includes is None:
        includes = ["*"]
    else:
        includes = Includes
    print_info(f"🔎 grep_search | Path: {SearchPath} | Query: '{Query}' | CaseInsensitive: {CaseInsensitive} | MatchPerLine: {MatchPerLine} | Includes: {includes}")

    import re
    results = []
    ignore_patterns = load_gitignore_patterns()
    flags = re.IGNORECASE if CaseInsensitive else 0
    regex = re.compile(Query, flags)
    found_files = set()

    def should_include(filename):
        for pattern in includes:
            if fnmatch.fnmatch(filename, pattern):
                return True
        return False

    if os.path.isfile(SearchPath):
        files_to_search = [SearchPath] if should_include(os.path.basename(SearchPath)) else []
    else:
        files_to_search = []
        for root, dirs, files in os.walk(SearchPath):
            dirs, files = filter_ignored(root, dirs, files, ignore_patterns)
            for file in files:
                filepath = os.path.join(root, file)
                if should_include(file):
                    files_to_search.append(filepath)

    for filepath in files_to_search:
        try:
            with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
                for lineno, line in enumerate(f, start=1):
                    if regex.search(line):
                        if MatchPerLine:
                            results.append(f"{filepath}:{lineno}:{line.rstrip()}")
                        else:
                            found_files.add(filepath)
                            break
        except Exception as e:
            print_error(f"❌ Error reading file '{filepath}': {e}")
            continue

    if not MatchPerLine:
        results = sorted(found_files)
    print_success(f"✅ Found {format_number(len(results))} matches")
    return "\n".join(results)
