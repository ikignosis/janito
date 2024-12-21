from dataclasses import dataclass
from typing import List

@dataclass
class MatchResult:
    start: int
    end: int
    strategy: str

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
                return MatchResult(i, i + len(find_lines), 'exact')
                
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
        def get_indentation(line: str) -> int:
            return len(line) - len(line.lstrip())

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
                    for line in [l.strip() for l in find_lines]:
                        print(f"  |{line}|")
                    print(f"Found indentation match at line {i+1}")
                return MatchResult(i, i + len(find_lines), 'indentation')
        
        if debug and found_any:
            print("No more indentation matches found")
        return None


class Finder:

    file_type_matchers = { 
        ".py": [ExactMatchStrategy, IndentationMatchStrategy],
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

    def replace(self, source_lines: List[str], match_result: MatchResult, replace_lines: List[str]) -> List[str]:
        # Use replacement indentation pattern, not source's pattern
        replaced = self._replace_indentation(match_result, source_lines, replace_lines)
        return source_lines[:match_result.start] + replaced + source_lines[match_result.end:]
        
    def _replace_indentation(self, match_result: MatchResult, source_lines: List[str], replace_lines: List[str]) -> List[str]:
        matched_text = source_lines[match_result.start:match_result.end]
        
        # Get the match position indentation
        match_indent_level = len(matched_text[0]) - len(matched_text[0].lstrip())
        
        # Get the replacement's structure
        non_empty_lines = [line for line in replace_lines if line.strip()]
        if not non_empty_lines:
            return replace_lines
            
        # Calculate base indentation from replacement's first line
        first_repl_indent = len(non_empty_lines[0]) - len(non_empty_lines[0].lstrip())
        
        # Process each line
        result = []
        for line in replace_lines:
            if not line.strip():
                result.append('')
                continue
                
            # Calculate this line's indent relative to replacement's first line
            current_indent = len(line) - len(line.lstrip())
            relative_indent = current_indent - first_repl_indent
            
            # Create new indent: match position + relative indent from replacement
            new_indent = ' ' * (match_indent_level + relative_indent)
            result.append(new_indent + line.lstrip())
            
        return result

class PatternNotFoundException(Exception):
    """Raised when a search pattern is not found in the source text"""
    pass

class FindReplacer:
    """
    Wraps Finder and Replacer into a single interface for common find-and-replace operations.
    Handles the typical pattern matching and replacement workflow.
    """
    
    def __init__(self, file_type: str = ".py"):
        self.finder = Finder()
        self.replacer = Replacer()
        self.file_type = file_type
        
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
            print("\nStarting find-replace operation:")
            print("Pattern to find:")
            print(find_pattern)
            print("\nReplacement:")
            print(replacement)
            
        # Convert to lines for processing
        source_lines = source.splitlines()
        find_lines = find_pattern.splitlines()
        replace_lines = replacement.splitlines()
        
        # Find the pattern
        match = self.finder.find(source_lines, find_lines, self.file_type, debug=debug)
        if not match:
            raise PatternNotFoundException("Pattern not found in source")
            
        # Replace the pattern
        result = self.replacer.replace(source_lines, match, replace_lines)
        
        if debug:
            print("\nReplacement successful")
            
        # Return as string
        return '\n'.join(result)

