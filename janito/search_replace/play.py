from pathlib import Path
from .searcher import Searcher
from typing import Optional
from . import SearchReplacer
import re

def _extract_file_ext(test_info: str) -> Optional[str]:
    """Extract file extension from test description."""
    # Try to find filename or extension in the test info
    ext_match = re.search(r'\.([a-zA-Z0-9]+)\b', test_info)
    if (ext_match):
        return f".{ext_match.group(1).lower()}"
    
    # Look for language mentions
    lang_map = {
        'python': '.py',
        'javascript': '.js',
        'typescript': '.ts',
        'java': '.java'
    }
    
    for lang, ext in lang_map.items():
        if lang.lower() in test_info.lower():
            return ext
            
    return None

def play_file(test_file: Optional[Path] = None):
    """Run search/replace tests from file"""
    searcher = Searcher()
    Searcher.set_debug(True)  # Enable debug mode for test runs

    if not test_file:
        print("No test file provided")
        return

    content = test_file.read_text()
    sections = content.split("========================================")
    
    if len(sections) < 3:
        print("Invalid test file format")
        return

    # Parse test file
    test_info = sections[0].strip()
    original = sections[1].replace("Original:", "").strip()
    search_pattern = sections[2].replace("Search pattern:", "").strip()

    # Determine file extension from test info
    file_ext = _extract_file_ext(test_info)

    # Display test file contents with clear separation
    print("\n" + "="*80)
    print("TEST FILE CONTENTS")
    print("="*80)
    print(f"Test description: {test_info}")
    print(f"Detected file extension: {file_ext or 'none'}")
    print("\nOriginal content:")
    print("-"*40)
    print(original)
    print("\nSearch pattern:")
    print("-"*40)
    print(search_pattern)
    
    # Display analysis with clear separation
    print("\n" + "="*80)
    print("PATTERN ANALYSIS")
    print("="*80)

    # Show available strategies
    strategies = searcher.get_strategies(file_ext)
    print("\nStrategies that will be tried in order:")
    for i, strategy in enumerate(strategies, 1):
        print(f"{i}. {strategy.__class__.__name__}")

    # Try to find pattern and show results
    print("\nMATCH ATTEMPTS")
    print("-"*40)
    
    searcher.debug_mode = True
    matches = searcher.exact_match(original, search_pattern)
    
    if matches:
        print(f"\nFound matches at lines: {matches}")
    else:
        print("\nNo exact matches found, trying flexible matching...")
        sr = SearchReplacer(original, search_pattern, file_ext=file_ext)
        if sr.find_pattern():
            print("Pattern found with flexible matching")
        else:
            print("\nRESULT: Pattern not found with any matching strategy")
            print("="*80)
