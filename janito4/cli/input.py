"""
CLI input handling for reading prompts from various sources.
"""

import sys


def read_stdin_prompt():
    """Read prompt from stdin if available.
    
    Returns:
        str or None: The prompt from stdin, or None if not available
    """
    if not sys.stdin.isatty():
        try:
            prompt = sys.stdin.read().strip()
            if prompt:
                return prompt
            else:
                print("Error: Empty prompt provided via stdin.", file=sys.stderr)
                sys.exit(1)
        except KeyboardInterrupt:
            print("\nOperation cancelled by user.", file=sys.stderr)
            sys.exit(130)
    return None
