"""Main entry point for search/replace module."""

from pathlib import Path
import sys
from .core import _run_tests

if __name__ == "__main__":
    test_file = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    if test_file and not test_file.exists():
        print(f"Test file not found: {test_file}")
        sys.exit(1)
    _run_tests(test_file)