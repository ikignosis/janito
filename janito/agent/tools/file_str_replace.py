import os
from janito.agent.tool_handler import ToolHandler
from janito.agent.tools.rich_utils import print_info, print_success, print_error, format_path

@ToolHandler.register_tool
def file_str_replace(path: str, old_string: str, new_string: str) -> str:
    """
    Replace a unique occurrence of a string in a file.

    path: Path to the file
    old_string: The exact string to replace
    new_string: The replacement string

    Returns a message indicating success, or an error if zero or multiple matches are found.
    """
    if not os.path.isfile(path):
        print_error(f"❌ Error: '{path}' is not a valid file.")
        return f"❌ Error: '{path}' is not a valid file."

    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print_error(f"❌ Error reading file: {e}")
        return f"❌ Failed to read file '{path}': {e}"

    num_matches = content.count(old_string)

    if num_matches == 0:
        print_info(f"ℹ️  No occurrences of the target string found in '{format_path(path)}'.")
        return f"ℹ️ No occurrences of the target string found in '{path}'."
    elif num_matches > 1:
        print_error(f"❌ Error: More than one occurrence ({num_matches}) of the target string found in '{format_path(path)}'. Aborting replacement.")
        return f"❌ Error: More than one occurrence ({num_matches}) of the target string found in '{path}'. Aborting replacement."

    new_content = content.replace(old_string, new_string, 1)

    try:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print_success(f"✅ Replaced the unique occurrence in '{format_path(path)}'.")
        return f"✅ Successfully replaced the unique occurrence in '{path}'."
    except Exception as e:
        print_error(f"❌ Error writing file: {e}")
        return f"❌ Failed to write updated content to '{path}': {e}"
