import os
from aurora.agent.tool_handler import ToolHandler
from aurora.agent.tools.rich_utils import print_info, print_success, print_error, format_path

@ToolHandler.register_tool
def file_str_replace(path: str, old_string: str, new_string: str, count: int = -1) -> str:
    """
    Replace exact occurrences of a string in a file.

    path: Path to the file
    old_string: The exact string to replace
    new_string: The replacement string
    count: Maximum number of replacements (-1 means replace all)

    Returns a message indicating success or failure and the number of replacements made.
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

    num_replacements = content.count(old_string) if count == -1 else min(content.count(old_string), count)

    if num_replacements == 0:
        print_info(f"ℹ️ No occurrences of the target string found in '{format_path(path)}'.")
        return f"ℹ️ No occurrences of the target string found in '{path}'."

    new_content = content.replace(old_string, new_string, count if count != -1 else content.count(old_string))

    try:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print_success(f"✅ Replaced {num_replacements} occurrence(s) in '{format_path(path)}'.")
        return f"✅ Successfully replaced {num_replacements} occurrence(s) in '{path}'."
    except Exception as e:
        print_error(f"❌ Error writing file: {e}")
        return f"❌ Failed to write updated content to '{path}': {e}"
