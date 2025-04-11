import os
from janito.agent.tool_handler import ToolHandler
from janito.agent.tools.rich_utils import print_info, print_success, print_error, format_path

@ToolHandler.register_tool
def create_file(path: str, content: str, overwrite: bool = False) -> str:
    """
    Create a file with the specified content.

    path: The path of the file to create
    content: The content to write into the file
    overwrite: Whether to overwrite the file if it exists (default: False)
    """
    old_lines = None
    if os.path.exists(path):
        if os.path.isdir(path):
            print_error("❌ Error: is a directory")
            return f"❌ Cannot create file: '{path}' is an existing directory."
        if overwrite:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    old_lines = sum(1 for _ in f)
            except Exception:
                old_lines = 'unknown'
        else:
            print_error(f"❗ Error: file '{path}' exists and overwrite is False")
            return f"❗ Cannot create file: '{path}' already exists and overwrite is False."

    new_lines = content.count('\n') + 1 if content else 0

    if old_lines is not None:
        print_info(f"♻️  Replacing file: '{format_path(path)}' (line count: {old_lines} -> {new_lines}) ... ")
    else:
        print_info(f"📝 Creating file: '{format_path(path)}' (lines: {new_lines}) ... ")

    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print_success("✅ Success")
        return f"✅ Successfully created the file at '{path}'."
    except Exception as e:
        print_error(f"❌ Error: {e}")
        return f"❌ Failed to create the file at '{path}': {e}"
