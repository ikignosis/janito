import os
import fnmatch
from janito.agent.tool_handler import ToolHandler
from janito.agent.tools.rich_utils import print_info, print_success, print_error, format_path, format_number
from janito.agent.tools.gitignore_utils import load_gitignore_patterns, filter_ignored

@ToolHandler.register_tool
def find_by_name(
    SearchDirectory: str,
    Pattern: str = "*",
    Excludes: list = None,
    Extensions: list = None,
    FullPath: bool = False,
    MaxDepth: int = None,
    Type: str = "any"
) -> str:
    # Show start info message
    info_msg = (
        f"🔍 find_by_name | Dir: {SearchDirectory} | Pattern: {Pattern} | Extensions: {Extensions if Extensions else 'Any'} | "
        f"Excludes: {Excludes if Excludes else 'None'} | MaxDepth: {MaxDepth if MaxDepth is not None else 'Unlimited'} | Type: {Type}"
    )
    print_info(info_msg)

    """
    Search for files and subdirectories within a specified directory using glob patterns, extensions, and filters.
    
    Files and directories matching .gitignore patterns are always ignored.

    Parameters:
      - Excludes (list of string, optional): Glob patterns to exclude from results.
      - Extensions (list of string, optional): File extensions to include (without dot).
      - FullPath (boolean, optional): If true, pattern matches the full path; otherwise, just the filename.
      - MaxDepth (integer, optional): Maximum directory depth to search.
      - Pattern (string, optional): Glob pattern to match filenames.
      - SearchDirectory (string, required): Directory to search within.
      - Type (string, optional): Filter by 'file', 'directory', or 'any'.
    """
    if Excludes is None:
        Excludes = []
    if Extensions is None:
        Extensions = []
    matches = []
    # Always ignore files/dirs matching .gitignore patterns
    ignore_patterns = load_gitignore_patterns()
    root_depth = SearchDirectory.rstrip(os.sep).count(os.sep)
    try:
        for root, dirs, files in os.walk(SearchDirectory):
            # MaxDepth check
            if MaxDepth is not None:
                current_depth = root.rstrip(os.sep).count(os.sep) - root_depth
                if current_depth >= MaxDepth:
                    dirs[:] = []  # Don't descend further
            # Filter out ignored files/dirs (from .gitignore)
            dirs, files = filter_ignored(root, dirs, files, ignore_patterns)
            # Exclude patterns (user-specified)
            for ex in Excludes:
                files = [f for f in files if not fnmatch.fnmatch(f, ex)]
                dirs = [d for d in dirs if not fnmatch.fnmatch(d, ex)]
            # Extensions filter
            if Extensions:
                files = [f for f in files if any(f.endswith('.' + ext) for ext in Extensions)]
            # Type filtering and pattern matching
            entries = []
            if Type in ("file", "any"):
                entries.extend([(f, os.path.join(root, f), "file") for f in files])
            if Type in ("directory", "any"):
                entries.extend([(d, os.path.join(root, d), "directory") for d in dirs])
            for name, path, entry_type in entries:
                match_target = path if FullPath else name
                if fnmatch.fnmatch(match_target, Pattern):
                    matches.append(path)
        print_success(f"✅ Found {format_number(len(matches))} entries")
        if matches:
            return "\n".join(matches)
        else:
            return "No matching entries found."
    except Exception as e:
        print_error(f"❌ Error: {e}")
        return f"❌ Failed to search in '{SearchDirectory}': {e}"
