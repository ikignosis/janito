import os
import shutil
from janito.agent.tool_handler import ToolHandler
from janito.agent.tools.rich_utils import print_info, print_success, print_error, format_path

@ToolHandler.register_tool
def create_file(path: str, content: str, overwrite: bool = False) -> str:
    """
    Create a new file or update an existing file with the given content.

    Args:
        path (str): Path to the file to create or update.
        content (str): Content to write to the file.
        overwrite (bool): Whether to overwrite the file if it exists.
    """
    updating = os.path.exists(path) and not os.path.isdir(path)
    if os.path.exists(path):
        if os.path.isdir(path):
            print_error("❌ Error: is a directory")
            return f"❌ Cannot create file: '{path}' is an existing directory."
        if not overwrite:
            print_error(f"❗ Error: file '{path}' exists and overwrite is False")
            return f"❗ Cannot create file: '{path}' already exists and overwrite is False."
    if updating and overwrite:
        print_info(f"📝 Updating file: '{format_path(path)}' ... ")
    else:
        print_info(f"📝 Creating file: '{format_path(path)}' ... ")
    old_lines = None
    if updating and overwrite:
        with open(path, "r", encoding="utf-8") as f:
            old_lines = sum(1 for _ in f)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print_success("✅ Success")
    if old_lines is not None:
        new_lines = content.count('\n') + 1 if content else 0
        return f"✅ Successfully updated the file at '{path}' ({old_lines} > {new_lines} lines)."
    else:
        return f"✅ Successfully created the file at '{path}'."


@ToolHandler.register_tool
def remove_file(path: str) -> str:
    print_info(f"🗑️  Removing file: '{format_path(path)}' ... ")
    os.remove(path)
    print_success("✅ Success")
    return f"✅ Successfully deleted the file at '{path}'."

@ToolHandler.register_tool
def move_file(source_path: str, destination_path: str, overwrite: bool = False) -> str:
    print_info(f"🚚 Moving '{format_path(source_path)}' to '{format_path(destination_path)}' ... ")
    if not os.path.exists(source_path):
        print_error("❌ Error: source does not exist")
        return f"❌ Source path '{source_path}' does not exist."
    if os.path.exists(destination_path):
        if not overwrite:
            print_error("❌ Error: destination exists and overwrite is False")
            return f"❌ Destination path '{destination_path}' already exists. Use overwrite=True to replace it."
        if os.path.isdir(destination_path):
            shutil.rmtree(destination_path)
        else:
            os.remove(destination_path)
    shutil.move(source_path, destination_path)
    print_success("✅ Success")
    return f"✅ Successfully moved '{source_path}' to '{destination_path}'."

@ToolHandler.register_tool
def create_directory(path: str) -> str:
    print_info(f"📁 Creating directory: '{format_path(path)}' ... ")
    os.makedirs(path, exist_ok=True)
    print_success("✅ Success")
    return f"✅ Directory '{path}' created successfully."
