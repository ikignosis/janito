"""Main entry point for search/replace module."""

from pathlib import Path
import sys
import argparse
from .play import play_file

if __name__ == "__main__":
        print("Usage: python -m janito.search_replace <test_file>")
        sys.exit(1)

    test_file = Path(sys.argv[1])
    if not test_file.exists():
        print(f"Test file not found: {test_file}")
        sys.exit(1)

    play_file(test_file)