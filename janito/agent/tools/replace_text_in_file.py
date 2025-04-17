import os
from janito.agent.tool_handler import ToolHandler
from janito.agent.tools.tool_base import ToolBase
from janito.agent.tools.rich_utils import print_info, print_success, print_error
from janito.agent.tools.utils import expand_path, display_path

def replace_text_in_file(file_path: str, search_text: str, replacement_text: str, replace_all: bool = False) -> str:
    """
    Replace exact occurrences of a given text in a file. The match must be exact, including whitespace and indentation, to avoid breaking file syntax or formatting.
    Args:
        file_path (str): Path to the plain text file.
        search_text (str): Text to search for (exact match).
        replacement_text (str): Text to replace search_text with.
        replace_all (bool): Whether to replace all occurrences or just the first. Default is False.
    Returns:
        str: Result message.
    """
    original_path = file_path
    file_path = expand_path(file_path)
    disp_path = display_path(original_path, file_path)
    search_preview = (search_text[:15] + '...') if len(search_text) > 15 else search_text
    replace_preview = (replacement_text[:15] + '...') if len(replacement_text) > 15 else replacement_text
    replace_all_msg = f" | Replace all: True" if replace_all else ""
    print_info(f"📝 Replacing text in file: '{disp_path}' | Search: '{search_preview}' | Replacement: '{replace_preview}'{replace_all_msg}")
    if not os.path.isfile(file_path):
        print_error(f"❌ File not found: {disp_path}")
        return f"❌ Error: File not found: {disp_path}"
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except PermissionError:
        print_error(f"❌ Permission denied: {disp_path}")
        return f"❌ Error: Permission denied: {disp_path}"
    except Exception as e:
        print_error(f"❌ Error reading file: {e}")
        return f"❌ Error reading file: {e}"

    count = content.count(search_text)
    if count == 0:
        print_info(f"ℹ️  Search text not found in file.")
        return f"ℹ️ No occurrences of search text found in '{disp_path}'."
    if replace_all:
        new_content = content.replace(search_text, replacement_text)
        replaced_count = count
    else:
        if count > 1:
            # Find line numbers where search_text appears
            lines = content.splitlines()
            found_lines = [i+1 for i, line in enumerate(lines) if search_text in line]
            preview = search_text[:40] + ('...' if len(search_text) > 40 else '')
            print_error(f"❌ Search text found multiple times ({count}). Please provide a more exact match or set replace_all=True.")
            return (
                f"❌ Error: Search text found {count} times in '{disp_path}'. "
                f"Preview: '{preview}'. Found at lines: {found_lines}. "
                f"Please provide a more exact match."
            )
        new_content = content.replace(search_text, replacement_text, 1)
        replaced_count = 1 if count == 1 else 0
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)
    except Exception as e:
        print_error(f"❌ Error writing file: {e}")
        return f"❌ Error writing file: {e}"
            # Find all line numbers where replacement occurred
    lines = content.splitlines()
    match_lines = [i+1 for i, line in enumerate(lines) if search_text in line]
    if replaced_count > 0:
        if len(match_lines) == 1:
            reference = f"{original_path}:{match_lines[0]}"
            print_success(f"✅ Replaced 1 occurrence in '{disp_path}' at line: {match_lines[0]}")
            return reference
        else:
            references = '\n'.join([f"{original_path}:{ln}" for ln in match_lines])
            print_success(f"✅ Replaced {replaced_count} occurrence(s) in '{disp_path}' at lines: {match_lines}")
            return references
    else:
        print_success(f"✅ No replacements made in '{disp_path}'")
        return f"No replacements made in '{disp_path}'"

class ReplaceTextInFileTool(ToolBase):
    """Replace exact occurrences of a given text in a file."""
    def call(self, file_path: str, search_text: str, replacement_text: str, replace_all: bool = False) -> str:
        return replace_text_in_file(file_path, search_text, replacement_text, replace_all)

ToolHandler.register_tool(ReplaceTextInFileTool, name="replace_text_in_file")
