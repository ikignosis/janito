from typing import Tuple

def create_progress_header(operation: str, filename: str, current: int, total: int,
                         reason: str = None, style: str = "cyan") -> Tuple[str, str]:
    """Create a compact single-line header with balanced layout.

    Args:
        operation: Type of operation being performed
        filename: Name of the file being modified
        current: Current change number
        total: Total number of changes
        reason: Optional reason for the change
        style: Color style for the header

    Returns:
        Tuple of (header text, style)
    """
    header = f"{operation} {filename} ({current}/{total})"
    if reason:
        header += f" - {reason}"
    return header, style 