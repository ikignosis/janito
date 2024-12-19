import ast
# ...existing code...
# Remove the process_change_request function if it exists in this file
# Keep all other existing code
from pathlib import Path
from typing import Optional, Tuple, List, Set
from rich.console import Console
from rich.prompt import Confirm
from rich.panel import Panel
from rich.columns import Columns
from rich import box

from janito.common import progress_send_message
from janito.change.history import save_changes_to_history
from janito.config import config
from janito.workspace import workset  # Updated import
from .viewer import preview_all_changes
from .parser import FileChange, ChangeOperation

from .analysis import analyze_request

def validate_file_operations(changes: List[FileChange], collected_files: Set[Path]) -> Tuple[bool, str]:
    """Validate file operations against current filesystem state.

    Validates:
    - Path conflicts:
        - Parent directory exists and is a directory
        - No Python module name conflicts (dir vs file)
    - Text modifications:
        - Search content required for non-append modifications
        - Replace content required for append operations

    Args:
        changes: List of file changes to validate
        collected_files: Set of files that were found during scanning

    Returns:
        Tuple[bool, str]: (is_valid, error_message)
    """
    for change in changes:
        # For modify operations, validate text changes
        if change.operation == ChangeOperation.MODIFY_FILE:
            for mod in change.text_changes:
                if not mod.is_delete and not mod.is_append:
                    if not mod.search_content:
                        return False, f"Search content required for modification in {change.name}"
                
                if mod.is_append and not mod.replace_content:
                    return False, f"Replace content required for append operation in {change.name}"

        # Check for directory/file conflicts
        if change.operation == ChangeOperation.CREATE_FILE:
            parent = change.name.parent
            if parent.exists() and not parent.is_dir():
                return False, f"Cannot create file - parent path exists as file: {parent}"

            # Check for Python module conflicts 
            if change.name.suffix == '.py':
                module_dir = change.name.with_suffix('')
                if module_dir.exists() and module_dir.is_dir():
                    return False, f"Cannot create Python file - directory with same name exists: {module_dir}"

        # Basic rename validation (without existence checks)
        if change.operation == ChangeOperation.RENAME_FILE:
            if not change.source or not change.target:
                return False, "Rename operation requires both source and target paths"

    return True, ""
from pathlib import Path
from typing import Tuple, List, Set, Optional
from .parser import FileChange, ChangeOperation

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

def validate_change(change: FileChange) -> Tuple[bool, Optional[str]]:
    """Validate a single FileChange object for structural correctness.
    
    Validates:
    - Required fields (name, operation type)
    - Operation-specific requirements:
        - Create/Replace: content is required
        - Rename: target path is required
        - Modify: at least one text change required
    - Text change validations:
        - Append: replace_content is required
        - Delete: search_content is required
        - Replace: both search_content and replace_content required
        - Prevents duplicate search patterns

    Args:
        change: FileChange object to validate

    Returns:
        Tuple[bool, Optional[str]]: (is_valid, error_message)
    """
    if not change.name:
        return False, "File name is required"

    operation = change.operation.name.title().lower()
    if operation not in ['create_file', 'replace_file', 'remove_file', 'rename_file', 'modify_file', 'move_file']:
        return False, f"Invalid file operation: {change.operation}"

    if operation in ['rename_file', 'move_file'] and not change.target:
        return False, "Target file path is required for rename/move operation"

    if operation in ['create_file', 'replace_file']:
        if not change.content:
            return False, f"Content is required for {change.operation} operation"

    if operation == 'modify_file':
        if not change.text_changes:
            return False, "At least one modification is required for modify operation"
            
        # Track search texts to avoid duplicates
        seen_search_texts = set()
        for mod in change.text_changes:
            # Validate append operations
            if mod.is_append:
                if not mod.replace_content:
                    return False, "Replace content required for append operation"
            # Validate other operations
            elif not mod.is_delete:
                if not mod.search_content:
                    return False, "Search content required for non-append modification"
                    
            if mod.search_content:
                seen_search_texts.add(mod.search_content)

    return True, None

def validate_all_changes(changes: List[FileChange], collected_files: Set[Path]) -> Tuple[bool, Optional[str]]:
    """Validates all aspects of the requested changes.

    Performs complete validation in two phases:
    1. Individual change validation:
        - Structure and content requirements
        - Operation-specific validations
        - Text modification validations
    2. Filesystem state validation:
        - File existence checks
        - Path conflict checks
        - Python module conflict checks

    Args:
        changes: List of changes to validate
        collected_files: Set of files found during scanning

    Returns:
        Tuple[bool, Optional[str]]: (is_valid, error_message)
        - If valid, error_message will be None
        - If invalid, error_message will describe the validation failure
    """
    # First validate individual changes
    for change in changes:
        is_valid, error = validate_change(change)
        if not is_valid:
            return False, f"Invalid change for {change.name}: {error}"
    
    # Then validate file operations against filesystem
    is_valid, error = validate_file_operations(changes, collected_files)
    if not is_valid:
        return False, error
        
    return True, None

def validate_file_operations(changes: List[FileChange], collected_files: Set[Path]) -> Tuple[bool, str]:
    """Validate file operations against current filesystem state.

    Validates:
    - File existence for operations that require it:
        - Modify: file must exist in collected files
        - Replace: file must exist in collected files
        - Remove: file must exist in collected files
    - File non-existence for operations that require it:
        - Create: file must not exist (unless marked as new)
        - Rename target: target must not exist
    - Path conflicts:
        - Parent directory exists and is a directory
        - No Python module name conflicts (dir vs file)
    - Text modifications:
        - Search content required for non-append modifications
        - Replace content required for append operations

    Args:
        changes: List of file changes to validate
        collected_files: Set of files that were found during scanning, includes state metadata

    Returns:
        Tuple[bool, str]: (is_valid, error_message)
    """
    for change in changes:
        # For modify operations, validate text changes
        if change.operation == ChangeOperation.MODIFY_FILE:
            for mod in change.text_changes:
                if not mod.is_delete and not mod.is_append:
                    if not mod.search_content:
                        return False, f"Search content required for modification in {change.name}"
                
                if mod.is_append and not mod.replace_content:
                    return False, f"Replace content required for append operation in {change.name}"

        # Get file state if available
        file_state = change.name.name.split(' (')[-1].rstrip(')') if ' (' in str(change.name) else None
        is_new_file = file_state == 'new' if file_state else False

        # Validate file exists for operations requiring it
        if change.operation in (ChangeOperation.MODIFY_FILE, ChangeOperation.REPLACE_FILE, ChangeOperation.REMOVE_FILE):
            if change.name not in collected_files and not is_new_file:
                return False, f"File not found in scanned files: {change.name}"


        # Validate rename/move operations
        if change.operation in (ChangeOperation.RENAME_FILE, ChangeOperation.MOVE_FILE):
            if not change.source or not change.target:
                return False, "Rename/move operation requires both source and target paths"
            if change.source not in collected_files and not is_new_file:
                return False, f"Source file not found for rename/move: {change.source}"

    return True, ""

def process_change_request(request: str) -> None:
    """Process a change request by analyzing, validating and applying changes."""
    # Ensure workset is refreshed before processing changes
    workset.refresh()
    
    # Analyze the request and get proposed changes
    changes = analyze_request(request, workset._workspace.content)
    if not changes:
        return

    # Collect the set of scanned files from workspace content
    collected_files = {Path(line.replace('<path>', '').replace('</path>', '').strip()) 
                      for line in workset._workspace.content.split('\n') 
                      if line.startswith('<path>')}

    # Validate changes
    is_valid, error = validate_all_changes(changes, collected_files)
    if not is_valid:
        console = Console()
        console.print(f"\n[red]Error:[/red] {error}")
        return

    # ...rest of existing function code...