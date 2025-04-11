import os
from janito.agent.tool_handler import ToolHandler
from janito.agent.tools.rich_utils import print_info, print_success, print_error, format_path

@ToolHandler.register_tool
def create_directory(path: str) -> str:
    """
    Create a directory at the specified path.

    path: The path of the directory to create
    """
    print_info(f"📁 Creating directory: '{format_path(path)}' ... ")
    try:
        os.makedirs(path, exist_ok=True)
        print_success("✅ Success")
        return f"✅ Directory '{path}' created successfully."
    except Exception as e:
        print_error(f"❌ Error: {e}")
        return f"❌ Error creating directory '{path}': {e}"
