
from typing import List, Tuple
from janito.config import config
from rich.console import Console

def get_line_boundaries(text: str) -> List[Tuple[int, int, int, int]]:
    """Return list of (content_start, content_end, full_start, full_end) for each line.
    content_start/end exclude leading/trailing whitespace
    full_start/end include the whitespace and line endings"""
    boundaries = []
    start = 0
    for line in text.splitlines(keepends=True):
        content = line.strip()
        if content:
            content_start = start + len(line) - len(line.lstrip())
            content_end = start + len(line.rstrip())
            boundaries.append((content_start, content_end, start, start + len(line)))
        else:
            # Empty or whitespace-only lines
            boundaries.append((start, start, start, start + len(line)))
        start += len(line)
    return boundaries

def normalize_content(text: str) -> Tuple[str, List[Tuple[int, int, int, int]]]:
    """Normalize text for searching while preserving position mapping.
    Returns (normalized_text, line_boundaries)"""
    # Replace Windows line endings
    text = text.replace('\r\n', '\n')
    text = text.replace('\r', '\n')
    
    # Get line boundaries before normalization
    boundaries = get_line_boundaries(text)
    
    # Create normalized version with stripped lines
    normalized = '\n'.join(line.strip() for line in text.splitlines())
    
    return normalized, boundaries

def find_text_positions(text: str, search: str) -> List[Tuple[int, int]]:
    """Find all non-overlapping positions of search text in content,
    comparing without leading/trailing whitespace but returning original positions."""
    normalized_text, text_boundaries = normalize_content(text)
    normalized_search, search_boundaries = normalize_content(search)
    
    positions = []
    start = 0
    while True:
        # Find next occurrence in normalized text
        pos = normalized_text.find(normalized_search, start)
        if pos == -1:
            break
            
        # Find the corresponding original text boundaries
        search_lines = normalized_search.count('\n') + 1
        
        # Get text line number at position
        line_num = normalized_text.count('\n', 0, pos)
        
        if line_num + search_lines <= len(text_boundaries):
            # Get original start position from first line
            orig_start = text_boundaries[line_num][2]  # full_start
            # Get original end position from last line
            orig_end = text_boundaries[line_num + search_lines - 1][3]  # full_end
            
            positions.append((orig_start, orig_end))
        
        start = pos + len(normalized_search)
    
    return positions

def format_whitespace_debug(text: str) -> str:
    """Format text with visible whitespace markers"""
    return text.replace(' ', '·').replace('\t', '→').replace('\n', '↵\n')

def format_context_preview(lines: List[str], max_lines: int = 5) -> str:
    """Format context lines for display, limiting the number of lines shown"""
    if not lines:
        return "No context lines"
    preview = lines[:max_lines]
    suffix = f"\n... and {len(lines) - max_lines} more lines" if len(lines) > max_lines else ""
    return "\n".join(preview) + suffix

