import ast
from pathlib import Path
from typing import Tuple

# Track validation statistics
validation_count = 0
validation_success = 0

from typing import Tuple, Optional
import ast

def validate_python_syntax(file_path: Path) -> Tuple[bool, str, Optional[str], Optional[str]]:
    """Validate Python file syntax using AST.

    Args:
        file_path: Path to the Python file to validate

    Returns:
        Tuple of (is_valid, error_message, code_line, pointer)
        where code_line is the line containing the error
        and pointer shows the error position with ^
    """
    global validation_count, validation_success
    validation_count += 1
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.splitlines()
        ast.parse(content, filename=str(file_path))
        validation_success += 1
        return True, "", None, None
    except SyntaxError as e:
        code_line = lines[e.lineno - 1] if e.lineno <= len(lines) else None
        pointer = ' ' * (e.offset - 1) + '^' if e.offset else None
        return False, f"Syntax error at line {e.lineno}: {e.msg}", code_line, pointer
    except Exception as e:
        return False, f"Error validating syntax: {str(e)}", None, None
