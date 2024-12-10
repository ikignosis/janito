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
