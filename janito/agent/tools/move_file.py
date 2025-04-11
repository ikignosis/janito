import shutil
import os
from janito.agent.tool_handler import ToolHandler
from janito.agent.tools.rich_utils import print_info, print_success, print_error, format_path


@ToolHandler.register_tool
def move_file(source_path: str, destination_path: str, overwrite: bool = False) -> str:
    """
    Move a file or directory from source_path to destination_path.

    source_path: The path of the file or directory to move
    destination_path: The target path
    overwrite: Whether to overwrite the destination if it exists (default: False)
    """
    print_info(f"🚚 Moving '{format_path(source_path)}' to '{format_path(destination_path)}' ... ")
    try:
        if not os.path.exists(source_path):
            print_error("❌ Error: source does not exist")
            return f"❌ Source path '{source_path}' does not exist."

        if os.path.exists(destination_path):
            if not overwrite:
                print_error("❌ Error: destination exists and overwrite is False")
                return f"❌ Destination path '{destination_path}' already exists. Use overwrite=True to replace it."
            # Remove destination if overwrite is True
            if os.path.isdir(destination_path):
                shutil.rmtree(destination_path)
            else:
                os.remove(destination_path)

        shutil.move(source_path, destination_path)
        print_success("✅ Success")
        return f"✅ Successfully moved '{source_path}' to '{destination_path}'."
    except Exception as e:
        print_error(f"❌ Error: {e}")
        return f"❌ Failed to move '{source_path}' to '{destination_path}': {e}"
