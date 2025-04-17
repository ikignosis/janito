import os
import shutil
from janito.agent.tool_handler import ToolHandler
from janito.agent.tools.rich_utils import print_info, print_success, print_error
from janito.agent.tools.utils import expand_path, display_path
from janito.agent.tools.tool_base import ToolBase

# Helper remains as-is
def _is_dir_empty(path):
    return not any(os.scandir(path))

class RemoveDirectoryTool(ToolBase):
    """Remove a directory. If recursive=False and directory not empty, raises error."""
    def call(self, path: str, recursive: bool = False) -> str:
        original_path = path
        path = expand_path(path)
        disp_path = display_path(original_path, path)
        if not os.path.exists(path):
            print_error(f"❌ Directory '{disp_path}' does not exist.")
            return f"❌ Directory '{disp_path}' does not exist."
        if not os.path.isdir(path):
            print_error(f"❌ Path '{disp_path}' is not a directory.")
            return f"❌ Path '{disp_path}' is not a directory."
        if recursive:
            print_info(f"🗑️  Recursively removing directory: '{disp_path}' ... ")
            shutil.rmtree(path)
            print_success("✅ Success")
            return f"✅ Successfully removed directory and all contents at '{disp_path}'."
        else:
            if not _is_dir_empty(path):
                print_error(f"❌ Directory '{disp_path}' is not empty. Use recursive=True to remove non-empty directories.")
                return f"❌ Directory '{disp_path}' is not empty. Use recursive=True to remove non-empty directories."
            print_info(f"🗑️  Removing empty directory: '{disp_path}' ... ")
            os.rmdir(path)
            print_success("✅ Success")
            return f"✅ Successfully removed empty directory at '{disp_path}'."

ToolHandler.register_tool(RemoveDirectoryTool, name="remove_directory")
