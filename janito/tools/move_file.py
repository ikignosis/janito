"""
Tool for moving files through the claudine agent.
"""
import shutil
from pathlib import Path
from typing import Tuple
from janito.tools.str_replace_editor.utils import normalize_path
from janito.tools.rich_console import print_info, print_success, print_error
from janito.tools.usage_tracker import track_usage


@track_usage('files_moved')
def move_file(
    source_path: str,
    destination_path: str,
) -> Tuple[str, bool]:
    """
    Move a file from source path to destination path.
    
    Args:
        source_path: Path to the file to move, relative to the workspace directory
        destination_path: Destination path where the file should be moved, relative to the workspace directory
        
    Returns:
        A tuple containing (message, is_error)
    """
    print_info(f"Moving file from {source_path} to {destination_path}", "Move Operation")
    
    # Store the original paths for display purposes
    original_source = source_path
    original_destination = destination_path
    
    # Normalize the file paths (converts to absolute paths)
    source = normalize_path(source_path)
    destination = normalize_path(destination_path)
    
    # Convert to Path objects for better path handling
    source_obj = Path(source)
    destination_obj = Path(destination)
    
    # Check if the source file exists
    if not source_obj.exists():
        error_msg = f"Source file {original_source} does not exist."
        print_error(error_msg, "Error")
        return (error_msg, True)
    
    # Check if source is a directory
    if source_obj.is_dir():
        error_msg = f"{original_source} is a directory, not a file. Use move_directory for directories."
        print_error(error_msg, "Error")
        return (error_msg, True)
    
    # Check if destination directory exists
    if not destination_obj.parent.exists():
        try:
            destination_obj.parent.mkdir(parents=True, exist_ok=True)
            print_info(f"Created directory: {destination_obj.parent}", "Info")
        except Exception as e:
            error_msg = f"Error creating destination directory: {str(e)}"
            print_error(error_msg, "Error")
            return (error_msg, True)
    
    # Move the file
    try:
        shutil.move(str(source_obj), str(destination_obj))
        success_msg = f"Successfully moved file from {original_source} to {original_destination}"
        print_success(success_msg, "Success")
        return (success_msg, False)
    except Exception as e:
        error_msg = f"Error moving file from {original_source} to {original_destination}: {str(e)}"
        print_error(error_msg, "Error")
        return (error_msg, True)