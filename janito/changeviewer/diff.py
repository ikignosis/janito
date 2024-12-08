from typing import List, Tuple

def find_common_sections(search_lines: List[str], replace_lines: List[str]) -> Tuple[List[str], List[str], List[str], List[str], List[str]]:
    """Find common sections between search and replace content"""
    # Find common lines from top
    common_top = []
    for s, r in zip(search_lines, replace_lines):
        if s == r:
            common_top.append(s)
        else:
            break
            
    # Find common lines from bottom
    search_remaining = search_lines[len(common_top):]
    replace_remaining = replace_lines[len(common_top):]
    
    common_bottom = []
    for s, r in zip(reversed(search_remaining), reversed(replace_remaining)):
        if s == r:
            common_bottom.insert(0, s)
        else:
            break
            
    # Get the unique middle sections
    search_middle = search_remaining[:-len(common_bottom)] if common_bottom else search_remaining
    replace_middle = replace_remaining[:-len(common_bottom)] if common_bottom else replace_remaining
    
    return common_top, search_middle, replace_middle, common_bottom, search_lines
