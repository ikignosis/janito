"""Text file validator for UTF-8 encoding validation."""

import codecs
from pathlib import Path


def validate_txt(path: str) -> str:
    """
    Validate a text file for UTF-8 encoding issues.
    
    Args:
        path (str): Path to the text file to validate
        
    Returns:
        str: Validation status message
            - "✅ Syntax OK" if file is valid UTF-8
            - "⚠️ Warning: UTF-8 decoding error: <error details>" if invalid
    """
    try:
        # Try to read the file with UTF-8 encoding
        with codecs.open(path, 'r', encoding='utf-8') as f:
            # Read the entire file to trigger any decoding errors
            f.read()
        return "✅ Syntax OK"
    except UnicodeDecodeError as e:
        return f"⚠️ Warning: UTF-8 decoding error: {e}"
    except Exception as e:
        return f"⚠️ Warning: File read error: {e}"