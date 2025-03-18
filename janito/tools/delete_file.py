"""
Tool for deleting files through the claudine agent.
"""
from pathlib import Path
from typing import Tuple
from janito.tools.str_replace_editor.utils import normalize_path
from janito.tools.rich_console import print_info, print_success, print_error
from janito.tools.usage_tracker import track_usage, get_tracker


@track_usage('files_deleted')
def delete_file(
    file_path: str,
) -> Tuple[str, bool]:
    """
    Delete an existing file.
    
    Args:
        file_path: Path to the file to delete, relative to the workspace directory
        
    Returns:
        A tuple containing (message, is_error)
    """
    print_info(f"Deleting file {file_path}", "Delete Operation")
    # Store the original path for display purposes
    original_path = file_path
    
    # Normalize the file path (converts to absolute path)
    path = normalize_path(file_path)
    
    # Convert to Path object for better path handling
    path_obj = Path(path)
    
    # Check if the file exists
    if not path_obj.exists():
        error_msg = f"File {original_path} does not exist."
        print_error(error_msg, "Error")
        return (error_msg, True)
    
    # Check if it's a directory
    if path_obj.is_dir():
        error_msg = f"{original_path} is a directory, not a file. Use delete_directory for directories."
        print_error(error_msg, "Error")
        return (error_msg, True)
    
    # Delete the file
    try:
        # Count the number of lines in the file before deleting
        try:
            with open(path_obj, 'r', encoding='utf-8') as f:
                line_count = len(f.readlines())
            # Track negative line delta for deleted file
            get_tracker().increment('lines_delta', -line_count)
        except Exception:
            # If we can't read the file, we can't count lines
            pass
            
        path_obj.unlink()
        success_msg = f"Successfully deleted file {original_path}"
        print_success("", "Success")
        return (success_msg, False)
    except Exception as e:
        error_msg = f"Error deleting file {original_path}: {str(e)}"
        print_error(error_msg, "Error")
        return (error_msg, True)
