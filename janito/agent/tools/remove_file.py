import os
from janito.agent.tool_handler import ToolHandler
from janito.agent.tools.rich_utils import print_info, print_success, print_error, format_path

@ToolHandler.register_tool
def remove_file(path: str) -> str:
    """
    Remove a specified file.

    path: The path of the file to remove
    """
    print_info(f"🗑️ Removing file: '{format_path(path)}' ... ")
    try:
        os.remove(path)
        print_success("✅ Success")
        return f"✅ Successfully deleted the file at '{path}'."
    except Exception as e:
        print_error(f"❌ Error: {e}")
        return f"❌ Failed to delete the file at '{path}': {e}"
