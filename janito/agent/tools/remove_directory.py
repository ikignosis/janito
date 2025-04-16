import os
import shutil
from janito.agent.tool_handler import ToolHandler
from janito.agent.tools.rich_utils import print_info, print_success, print_error, format_path

def _is_dir_empty(path):
    return not any(os.scandir(path))

@ToolHandler.register_tool
def remove_directory(path: str, recursive: bool = False) -> str:
    """
    Remove a directory. If recursive is False and the directory is not empty, return an error.

    Args:
        path (str): Path to the directory to remove.
        recursive (bool): Whether to remove non-empty directories recursively. Default is False.
    Returns:
        str: Result message.
    """
    if not os.path.exists(path):
        print_error(f"❌ Directory '{path}' does not exist.")
        return f"❌ Directory '{path}' does not exist."
    if not os.path.isdir(path):
        print_error(f"❌ Path '{path}' is not a directory.")
        return f"❌ Path '{path}' is not a directory."
    if recursive:
        print_info(f"🗑️  Recursively removing directory: '{format_path(path)}' ... ")
        shutil.rmtree(path)
        print_success("✅ Success")
        return f"✅ Successfully removed directory and all contents at '{path}'."
    else:
        if not _is_dir_empty(path):
            print_error(f"❌ Directory '{path}' is not empty. Use recursive=True to remove non-empty directories.")
            return f"❌ Directory '{path}' is not empty. Use recursive=True to remove non-empty directories."
        print_info(f"🗑️  Removing empty directory: '{format_path(path)}' ... ")
        os.rmdir(path)
        print_success("✅ Success")
        return f"✅ Successfully removed empty directory at '{path}'."
