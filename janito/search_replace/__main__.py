"""Main entry point for search/replace module."""

from pathlib import Path
import sys
import argparse
from .play import play_file

def main():
    parser = argparse.ArgumentParser(description="Debug search/replace patterns")
    parser.add_argument('file', type=Path, help='Test file to analyze')
    
    args = parser.parse_args()
    
    if not args.file.exists():
        print(f"Error: Test file not found: {args.file}")
        sys.exit(1)
        
    play_file(args.file)

if __name__ == "__main__":
    main()