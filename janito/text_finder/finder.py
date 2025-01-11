from dataclasses import dataclass, field
from typing import List
from rich.console import Console
from rich.syntax import Syntax

def get_indentation(line: str) -> int:
    return len(line) - len(line.lstrip())

@dataclass
class MatchResult:
    start: int  # Start index of the match (in the source lines)
    end: int    # End index of the match (in the source lines)
    strategy: str  # Strategy used to find the 
    find_lines: List[str] = field(default_factory=list)  # The lines that were used to find the match

class ExactMatchStrategy:

    @staticmethod    
    def find(source_lines: List[str], find_lines: List[str], debug: bool = False) -> MatchResult:
        if debug:
            print("\nAttempting exact match...")
                
        found_any = False
        for i in range(len(source_lines) - len(find_lines) + 1):
            match_lines = source_lines[i:i + len(find_lines)]
            if match_lines == find_lines:
                found_any = True
                if debug:
                    print("\nPattern to find:")
                    for line in find_lines:
                        print(f"  |{line}|")
                    print(f"Found exact match at line {i+1}")
                return MatchResult(find_lines=find_lines, start=i, end=i + len(find_lines), strategy='exact')
                
        if debug and found_any:
            print("No more exact matches found")
        return None


class IndentationMatchStrategy:
    """ 
    This strategy is used to find a block of code where the indentation might not be the same as the original code.
    The match will be successful if all lines are found in the same order and have the same relative indentation
    pattern (more/less indented than previous line), regardless of the actual indentation amount.
    """

    @staticmethod    
    def find(source_lines: List[str], find_lines: List[str], debug: bool = False) -> MatchResult:
        def get_indentation_pattern(lines: List[str]) -> List[str]:
            """Returns a list of '<', '>', '=' representing indentation changes"""
            result = []
            for i in range(1, len(lines)):
                prev_indent = get_indentation(lines[i-1])
                curr_indent = get_indentation(lines[i])
                if curr_indent > prev_indent:
                    result.append('>')
                elif curr_indent < prev_indent:
                    result.append('<')
                else:
                    result.append('=')
            return result
            
        if debug:
            print("\nAttempting indentation-aware match...")
        
        found_any = False
        for i in range(len(source_lines) - len(find_lines) + 1):
            # Check content
            stripped_source_lines = [line.strip() for line in source_lines[i:i + len(find_lines)]]
            stripped_find_lines = [line.strip() for line in find_lines]
            if stripped_source_lines != stripped_find_lines:
                continue

            # Check indentation pattern
            source_pattern = get_indentation_pattern(source_lines[i:i + len(find_lines)])
            find_pattern = get_indentation_pattern(find_lines)
            
            if source_pattern == find_pattern:
                found_any = True
                
                if debug:
                    print("\nPattern to find (stripped):")
                    for j, (src, pat) in enumerate(zip(source_lines[i:i + len(find_lines)], find_lines)):
                        src_indent = get_indentation(src)
                        pat_indent = get_indentation(pat)
                        if src_indent != pat_indent:
                            print(f"  |{pat.strip()}| (indent: {pat_indent} → {src_indent})")
                        else:
                            print(f"  |{pat.strip()}| (indent: {pat_indent})")
                    print(f"Found indentation match at line {i+1}")
                
                return MatchResult(find_lines=find_lines, start=i, end=i + len(find_lines), strategy='indentation')
        
        if debug and found_any:
            print("No more indentation matches found")
        return None


class BetweenContextsStrategy:
    """Strategy for finding content between two contexts."""
    
    @staticmethod
    def find(source_lines: List[str], find_lines: List[str], debug: bool = False) -> MatchResult:
        if debug:
            print("\nAttempting between-contexts match...")
            
        # Split the find pattern into start context, placeholder, and end context
        try:
            placeholder_idx = find_lines.index("    # ... any content between contexts ...")
            start_context = find_lines[:placeholder_idx]
            end_context = find_lines[placeholder_idx + 1:]
        except ValueError:
            return None
            
        # Find start context
        start_match = None
        for i in range(len(source_lines)):
            if all(line.strip() == start.strip() for line, start in zip(source_lines[i:], start_context)):
                start_match = i
                break
                
        if start_match is None:
            return None
            
        # Find end context after start match
        end_match = None
        for i in range(start_match + len(start_context), len(source_lines)):
            if all(line.strip() == end.strip() for line, end in zip(source_lines[i:], end_context)):
                end_match = i
                break
                
        if end_match is None:
            return None
            
        if debug:
            print(f"\nFound start context at line {start_match + 1}")
            print(f"Found end context at line {end_match + 1}")
            
        # Return match including both contexts and everything between them
        return MatchResult(
            find_lines=find_lines,
            start=start_match,
            end=end_match + len(end_context),
            strategy='between_contexts'
        )


class Finder:

    file_type_matchers = { 
        ".py": [BetweenContextsStrategy, ExactMatchStrategy, IndentationMatchStrategy],
    }

    def find(self, text_lines: List[str], find_lines: List[str], file_type: str, debug: bool = False) -> MatchResult:
        # Add the dot if not present
        if not file_type.startswith('.'):
            file_type = '.' + file_type
            
        if debug:
            print(f"\nSearching in file type: {file_type}")
            
        for strategy in self.file_type_matchers.get(file_type, [ExactMatchStrategy]):
            result = strategy.find(text_lines, find_lines, debug=debug)
            if result:
                return result
                
        if debug:
            print("\nNo matches found")


class Replacer:

    def __init__(self):
        self.console = Console()

    def replace(self, source_lines: List[str], match_result: MatchResult, replace_lines: List[str], debug: bool = False) -> List[str]:
        # Use replacement indentation pattern, not source's pattern
        replaced = self._replace_indentation(match_result, source_lines, replace_lines, debug)
        return source_lines[:match_result.start] + replaced + source_lines[match_result.end:]
        
    def _replace_indentation(self, match_result: MatchResult, source_lines: List[str], replace_lines: List[str], debug: bool = False) -> List[str]:
        matched_text = source_lines[match_result.start:match_result.end]
        
        # Get indentation of first matched line
        match_indent = get_indentation(matched_text[0])
        
        # Get the replacement's structure
        non_empty_lines = [line for line in replace_lines if line.strip()]
        
        # Empty lines means delete
        if not non_empty_lines:
            return []
        
        # For indentation matches, always apply the shift to all lines
        if match_result.strategy == 'indentation':
            
            # Calculate shift based on first line
            find_indent = get_indentation(match_result.find_lines[0])
            indent_shift = match_indent - find_indent
            
            if debug:
                self.console.print("\n[yellow]Adjusting all lines[/yellow]")
                self.console.print(f"Base indent shift: {indent_shift:+d} spaces")
                for i, line in enumerate(replace_lines):
                    current_indent = get_indentation(line)
                    self.console.print(f"Line {i+1}: {current_indent} → {current_indent + indent_shift}")
            
            # Apply shift to all lines
            return [' ' * (get_indentation(line) + indent_shift) + line.lstrip() 
                   for line in replace_lines]
        
        # For exact matches, keep original indentation
        if debug:
            self.console.print("\n[yellow]Exact match - keeping original indentation[/yellow]")
        
        return replace_lines

class PatternNotFoundException(Exception):
    """Raised when a search pattern is not found in the source text"""
    pass

class FindReplacer:
    """
    Wraps Finder and Replacer into a single interface for common find-and-replace operations.
    Handles the typical pattern matching and replacement workflow.
    """

    @classmethod
    def replay(cls, file_path: str) -> None:
        """Replay a search/replace operation from a saved diagnostic file.

        Args:
            file_path: Path to the diagnostic file containing the operation details
        """
        from pathlib import Path
        from rich.console import Console

        console = Console()

        try:
            content = Path(file_path).read_text(encoding='utf-8')
            source, find_pattern, replacement = content.split('---')

            find_replacer = cls()
            result = find_replacer.replace(source, find_pattern, replacement, debug=True)

            console.print("\n[green]Replay completed successfully![/green]")
            console.print("\n[bold]Result:[/bold]")
            console.print(result)
        except Exception as e:
            console.print(f"[red]Error during replay: {str(e)}[/red]")
    
    def __init__(self, file_type: str = ".py"):
        self.finder = Finder()
        self.replacer = Replacer()
        self.file_type = file_type
        self.console = Console()
        
    def replace(self, source: str, find_pattern: str, replacement: str, debug: bool = False) -> str:
        """
        Find a pattern in source and replace it with the replacement text.
        
        Args:
            source: Source code to modify
            find_pattern: Pattern to find
            replacement: Text to replace the pattern with
            debug: Whether to print debug information
            
        Returns:
            Modified source code with replacement applied
            
        Raises:
            PatternNotFoundException: If pattern is not found
        """
        if debug:
            self.console.print("\n[cyan]Starting find-replace operation:[/cyan]")
            
            # Show the pattern we're looking for
            self.console.print("\n[yellow]Pattern to find:[/yellow]")
            syntax = Syntax(find_pattern, "python", theme="monokai", line_numbers=True)
            self.console.print(syntax)
            
            # Show what we'll replace it with
            self.console.print("\n[green]Replacement:[/green]")
            syntax = Syntax(replacement, "python", theme="monokai", line_numbers=True)
            self.console.print(syntax)
            
        # Convert to lines for processing
        source_lines = source.splitlines()
        find_lines = find_pattern.splitlines()
        replace_lines = replacement.splitlines()
        
        # Find the pattern
        match = self.finder.find(source_lines, find_lines, self.file_type, debug=debug)
        if not match:
            raise PatternNotFoundException("Pattern not found in source")
            
        if debug:
            # Show the context of what we're replacing
            context_start = max(0, match.start - 2)
            context_end = min(len(source_lines), match.end + 2)
            
            self.console.print("\n[yellow]Replacing this section:[/yellow]")
            
            # Show lines before the match
            for i in range(context_start, match.start):
                indent = len(source_lines[i]) - len(source_lines[i].lstrip())
                if source_lines[i].strip():
                    self.console.print(f"  {i+1:4d} [{indent:2d}] | {source_lines[i]}")
                else:
                    self.console.print("")
                
            # Show the matched lines that will be replaced
            for i in range(match.start, match.end):
                indent = len(source_lines[i]) - len(source_lines[i].lstrip())
                if source_lines[i].strip():
                    self.console.print(f"[red]- {i+1:4d} [{indent:2d}] | {source_lines[i]}[/red]")
                else:
                    self.console.print("")
                
            # Show lines after the match
            for i in range(match.end, context_end):
                indent = len(source_lines[i]) - len(source_lines[i].lstrip())
                if source_lines[i].strip():
                    self.console.print(f"  {i+1:4d} [{indent:2d}] | {source_lines[i]}")
                else:
                    self.console.print("")
            
        # Replace the pattern
        result = self.replacer.replace(source_lines, match, replace_lines, debug=debug)
        
        if debug:
            # Show what it actually looks like after replacement
            self.console.print("\n[yellow]After replacement:[/yellow]")
            
            # Show lines before the replacement
            for i in range(context_start, match.start):
                indent = len(result[i]) - len(result[i].lstrip())
                if result[i].strip():
                    self.console.print(f"  {i+1:4d} [{indent:2d}] | {result[i]}")
                else:
                    self.console.print("")
                
            # Show the new lines
            for i in range(match.start, match.start + len(replace_lines)):
                indent = len(result[i]) - len(result[i].lstrip())
                if result[i].strip():
                    self.console.print(f"[green]+ {i+1:4d} [{indent:2d}] | {result[i]}[/green]")
                else:
                    self.console.print("")
                
            # Show lines after the replacement
            for i in range(match.start + len(replace_lines), context_end):
                if i < len(result):
                    indent = len(result[i]) - len(result[i].lstrip())
                    if result[i].strip():
                        self.console.print(f"  {i+1:4d} [{indent:2d}] | {result[i]}")
                    else:
                        self.console.print("")
            
            self.console.print("\n[cyan]Replacement complete[/cyan]")
            
        # Return as string
        return '\n'.join(result)

    def create_pattern_between_contexts(self, start_context: str, end_context: str) -> str:
        """Create a pattern that matches content between two contexts.
        
        Args:
            start_context: The starting context to match
            end_context: The ending context to match
            
        Returns:
            A pattern string that includes both contexts and everything between them
        """
        # Split contexts into lines and strip any trailing whitespace
        start_lines = [line.rstrip() for line in start_context.splitlines()]
        end_lines = [line.rstrip() for line in end_context.splitlines()]
        
        if not start_lines or not end_lines:
            raise ValueError("Both start and end contexts must not be empty")
            
        # Create a pattern that includes both contexts and everything between them
        pattern = []
        pattern.extend(start_lines)
        pattern.append("    # ... any content between contexts ...")
        pattern.extend(end_lines)
        
        return "\n".join(pattern)
