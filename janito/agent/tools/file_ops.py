import os
import shutil
from janito.agent.tool_handler import ToolHandler
from janito.agent.tools.rich_utils import print_info, print_success, print_error
from janito.agent.tools.utils import expand_path, display_path

@ToolHandler.register_tool
def create_file(path: str, content: str, overwrite: bool = False) -> str:
    """
    Create a new file or update an existing file with the given content.
    Args:
        path (str): Path to the file to create or update.
        content (str): Content to write to the file.
        overwrite (bool): Whether to overwrite the file if it exists.
    """
    original_path = path
    path = expand_path(path)
    updating = os.path.exists(path) and not os.path.isdir(path)
    disp_path = display_path(original_path, path)
    if os.path.exists(path):
        if os.path.isdir(path):
            print_error(f"❌ Error: is a directory")
            return f"❌ Cannot create file: '{disp_path}' is an existing directory."
        if not overwrite:
            print_error(f"❗ Error: file '{disp_path}' exists and overwrite is False")
            return f"❗ Cannot create file: '{disp_path}' already exists and overwrite is False."
    if updating and overwrite:
        print_info(f"📝 Updating file: '{disp_path}' ... ")
    else:
        print_info(f"📝 Creating file: '{disp_path}' ... ")
    old_lines = None
    if updating and overwrite:
        with open(path, "r", encoding="utf-8") as f:
            old_lines = sum(1 for _ in f)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print_success("✅ Success")
    if old_lines is not None:
        new_lines = content.count('\n') + 1 if content else 0
        return f"✅ Successfully updated the file at '{disp_path}' ({old_lines} > {new_lines} lines)."
    else:
        return f"✅ Successfully created the file at '{disp_path}'."

@ToolHandler.register_tool
def create_directory(path: str, overwrite: bool = False) -> str:
    """
    Create a new directory at the specified path.
    Args:
        path (str): Path to the directory to create.
        overwrite (bool): Whether to remove the directory if it exists.
    Returns:
        str: Result message.
    """
    original_path = path
    path = expand_path(path)
    disp_path = display_path(original_path, path)
    if os.path.exists(path):
        if not os.path.isdir(path):
            print_error(f"❌ Path '{disp_path}' exists and is not a directory.")
            return f"❌ Path '{disp_path}' exists and is not a directory."
        if not overwrite:
            print_error(f"❗ Directory '{disp_path}' already exists and overwrite is False.")
            return f"❗ Directory '{disp_path}' already exists and overwrite is False."
        # Remove existing directory if overwrite is True
        shutil.rmtree(path)
        print_info(f"🗑️  Removed existing directory: '{disp_path}'")
    os.makedirs(path, exist_ok=True)
    print_success(f"✅ Created directory: '{disp_path}'")
    return f"✅ Successfully created directory at '{disp_path}'."

@ToolHandler.register_tool
def remove_file(path: str) -> str:
    original_path = path
    path = expand_path(path)
    disp_path = display_path(original_path, path)
    print_info(f"🗑️  Removing file: '{disp_path}' ... ")
    os.remove(path)
    print_success("✅ Success")
    return f"✅ Successfully deleted the file at '{disp_path}'."

@ToolHandler.register_tool
def move_file(source_path: str, destination_path: str, overwrite: bool = False) -> str:
    orig_source = source_path
    orig_dest = destination_path
    source_path = expand_path(source_path)
    destination_path = expand_path(destination_path)
    disp_source = display_path(orig_source, source_path)
    disp_dest = display_path(orig_dest, destination_path)
    print_info(f"🚚 Moving '{disp_source}' to '{disp_dest}' ... ")
    if not os.path.exists(source_path):
        print_error(f"❌ Error: source does not exist")
        return f"❌ Source path '{disp_source}' does not exist."
    if os.path.exists(destination_path):
        if not overwrite:
            print_error(f"❗ Error: destination exists and overwrite is False")
            return f"❗ Destination path '{disp_dest}' already exists and overwrite is False."
        if os.path.isdir(destination_path):
            print_error(f"❌ Error: destination is a directory")
            return f"❌ Destination path '{disp_dest}' is an existing directory."
    shutil.move(source_path, destination_path)
    print_success("✅ Success")
    return f"✅ Successfully moved '{disp_source}' to '{disp_dest}'."
