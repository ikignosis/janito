import ast
from pathlib import Path
from typing import Tuple

# Track validation statistics
validation_count = 0
validation_success = 0

def validate_python_syntax(file_path: Path) -> Tuple[bool, str]:
    """Validate Python file syntax using AST.

    Args:
        file_path: Path to the Python file to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    global validation_count, validation_success
    validation_count += 1
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        ast.parse(content, filename=str(file_path))
        validation_success += 1
        return True, ""
    except SyntaxError as e:
        return False, f"Syntax error at line {e.lineno}: {e.msg}"
    except Exception as e:
        return False, f"Error validating syntax: {str(e)}"
