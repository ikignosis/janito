from pathlib import Path
from typing import Optional
from .parser import parse_test_file
from .core import SearchReplacer
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

def play_file(filepath: Path):
    """Play back a test file and show detailed debugging info."""
    test_cases = parse_test_file(filepath)
    
    for test in test_cases:
        print(f"\nTest: {test['name']}")
        print("=" * 50)
        
        if 'source' not in test or 'search' not in test:
            print("Invalid test case - missing source or search pattern")
            continue
            
        file_ext = _extract_file_ext(test['name'])
        print(f"\nFile type: {file_ext or 'unknown'}")
        
        replacer = SearchReplacer(
            source_code=test['source'],
            search_pattern=test['search'],
            replacement=test.get('replacement'),
            file_ext=file_ext,
            debug=True
        )
        
        try:
            print("\nAttempting search/replace...")
            result = replacer.replace()
            print("\nResult:")
            print("-" * 50)
            print(result)
            
        except Exception as e:
            print(f"\nError: {str(e)}")
        
        print("\n" + "="*50)
