from typing import List, Tuple, Optional, NamedTuple
from difflib import SequenceMatcher
from janito.config import config
from rich.console import Console

class ContextError(NamedTuple):
    """Contains error details for context matching failures"""
    pre_context: List[str]
    post_context: List[str]
    content: str

def parse_change_block(content: str) -> Tuple[List[str], List[str], List[str]]:
    """Parse a change block into pre-context, post-context and change lines.
    Returns (pre_context_lines, post_context_lines, change_lines)"""
    pre_context_lines = []
    post_context_lines = []
    change_lines = []
    in_pre_context = True
    
    for line in content.splitlines():
        if line.startswith('='):
            if in_pre_context:
                pre_context_lines.append(line[1:])
            else:
                post_context_lines.append(line[1:])
        elif line.startswith('>'):
            in_pre_context = False
            change_lines.append(line[1:])
            
    return pre_context_lines, post_context_lines, change_lines

def find_context_match(file_content: str, pre_context: List[str], post_context: List[str], min_context: int = 2) -> Optional[Tuple[int, int]]:
    """Find exact matching location using line-by-line matching.
    Returns (start_index, end_index) or None if no match found."""
    if not (pre_context or post_context) or (len(pre_context) + len(post_context)) < min_context:
        return None

    file_lines = file_content.splitlines()
    
    # Function to check if lines match at a given position
    def lines_match_at(pos: int, target_lines: List[str]) -> bool:
        if pos + len(target_lines) > len(file_lines):
            return False
        return all(a == b for a, b in zip(file_lines[pos:pos + len(target_lines)], target_lines))

    # For debug output
    debug_matches = []
    
    # Try to find pre_context match
    pre_match_pos = None
    if pre_context:
        for i in range(len(file_lines) - len(pre_context) + 1):
            if lines_match_at(i, pre_context):
                pre_match_pos = i
                break
            if config.debug:
                # Record first 20 non-matches for debug output
                if len(debug_matches) < 20:
                    debug_matches.append((i, file_lines[i:i + len(pre_context)]))

    # Try to find post_context match after pre_context if found
    if pre_match_pos is not None and post_context:
        expected_post_pos = pre_match_pos + len(pre_context)
        if not lines_match_at(expected_post_pos, post_context):
            pre_match_pos = None

    if pre_match_pos is None and config.debug:
        console = Console()
        console.print("\n[bold red]Context Match Debug:[/bold red]")
        
        if pre_context:
            console.print("\n[yellow]Expected pre-context:[/yellow]")
            for i, line in enumerate(pre_context):
                console.print(f"  {i+1:2d} | '{line}'")

        if post_context:
            console.print("\n[yellow]Expected post-context:[/yellow]")
            for i, line in enumerate(post_context):
                console.print(f"  {i+1:2d} | '{line}'")

        console.print("\n[yellow]First 20 attempted matches in file:[/yellow]")
        for pos, lines in debug_matches:
            console.print(f"\n[cyan]At line {pos+1}:[/cyan]")
            for i, line in enumerate(lines):
                match_status = "≠" if i < len(pre_context) and line != pre_context[i] else "="
                console.print(f"  {i+1:2d} | '{line}' {match_status}")

        return None

    if pre_match_pos is None:
        return None

    end_pos = pre_match_pos + len(pre_context)
    
    return pre_match_pos, end_pos

def apply_changes(content: str, 
                 pre_context_lines: List[str], 
                 post_context_lines: List[str], 
                 change_lines: List[str]) -> Optional[Tuple[str, Optional[ContextError]]]:
    """Apply changes with context matching, returns (new_content, error_details)"""
    if not content.strip() and not pre_context_lines and not post_context_lines:
        return '\n'.join(change_lines), None

    pre_context = '\n'.join(pre_context_lines)
    post_context = '\n'.join(post_context_lines)
    
    if pre_context and pre_context not in content:
        return None, ContextError(pre_context_lines, post_context_lines, content)
    
    if post_context and post_context not in content:
        return None, ContextError(pre_context_lines, post_context_lines, content)

