import ast
from pathlib import Path
from typing import Tuple

def validate_python_syntax(code: str, filepath: Path | str) -> Tuple[bool, str]:
    """Validate Python code syntax using ast parser.
    
    Args:
        code: Python source code to validate
        filepath: Path or string of the file (used for error messages)
        
    Returns:
        Tuple of (is_valid, error_message)
        - is_valid: True if syntax is valid
        - error_message: Empty string if valid, error details if invalid
    """
    try:
        ast.parse(code)
        return True, ""
    except SyntaxError as e:
        # Get detailed error information
        line_num = e.lineno if e.lineno is not None else 0
        col_num = e.offset if e.offset is not None else 0
        line = e.text or ""
        
        # Build error message with line pointer
        pointer = " " * (col_num - 1) + "^" if col_num > 0 else ""
        error_msg = (
            f"Syntax error at {filepath}:{line_num}:{col_num}\n"
            f"{line}\n"
            f"{pointer}\n"
            f"Error: {str(e)}"
        )
        return False, error_msg
    except Exception as e:
        return False, f"Parsing error in {filepath}: {str(e)}"
from pathlib import Path
from typing import Tuple, List, Set
from .parser import FileChange, ChangeOperation

def validate_file_operations(changes: List[FileChange], collected_files: Set[Path]) -> Tuple[bool, str]:
    """Validate file operations against current filesystem state.

    Args:
        changes: List of file changes to validate
        collected_files: Set of files that were collected during scanning

    Returns:
        Tuple of (is_valid, error_message)
    """
    for change in changes:
        # Validate file exists for operations requiring it
        if change.operation in (ChangeOperation.MODIFY_FILE, ChangeOperation.REPLACE_FILE, ChangeOperation.REMOVE_FILE):
            if change.name not in collected_files:
                return False, f"File not found in scanned files: {change.name}"

        # Validate file doesn't exist for create operations
        if change.operation == ChangeOperation.CREATE_FILE:
            if change.name in collected_files:
                return False, f"Cannot create file that already exists: {change.name}"

            # Check for directory/file conflicts
            parent = change.name.parent
            if parent.exists() and not parent.is_dir():
                return False, f"Cannot create file - parent path exists as file: {parent}"

            # Check for Python module conflicts
            if change.name.suffix == '.py':
                module_dir = change.name.with_suffix('')
                if module_dir.exists() and module_dir.is_dir():
                    return False, f"Cannot create Python file - directory with same name exists: {module_dir}"

        # Validate rename operations
        if change.operation == ChangeOperation.RENAME_FILE:
            if not change.source or not change.target:
                return False, "Rename operation requires both source and target paths"
            if change.source not in collected_files:
                return False, f"Source file not found for rename: {change.source}"
            if change.target in collected_files:
                return False, f"Cannot rename - target file already exists: {change.target}"

    return True, ""