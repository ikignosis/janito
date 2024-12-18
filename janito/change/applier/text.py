from typing import Tuple, List, Optional
from rich.console import Console
from pathlib import Path
from datetime import datetime
from ..parser import TextChange
from janito.config import config
from ...clear_statement_parser.parser import StatementParser
from ...search_replace import SearchReplacer, PatternNotFoundException, Searcher

class TextFindDebugger:
    def __init__(self, console: Console):
        self.console = console
        self.find_count = 0

    def _visualize_whitespace(self, text: str) -> str:
        """Convert whitespace characters to visible markers"""
        return text.replace(' ', '·').replace('\t', '→')

    def debug_find(self, content: str, search: str) -> List[int]:
        """Debug find operation by showing numbered matches"""
        self.find_count += 1
        matches = []

        # Show search pattern
        self.console.print(f"\n[cyan]Find #{self.find_count} search pattern:[/cyan]")
        for i, line in enumerate(search.splitlines()):
            self.console.print(f"[dim]{i+1:3d} | {self._visualize_whitespace(line)}[/dim]")

        # Process content line by line
        lines = content.splitlines()
        for i, line in enumerate(lines):
            if search.strip() in line.strip():
                matches.append(i + 1)
                self.console.print(f"[green]Match at line {i+1}:[/green] {self._visualize_whitespace(line)}")

        if not matches:
            self.console.print("[yellow]No matches found[/yellow]")

        return matches

class TextChangeApplier:
    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()
        self.debugger = TextFindDebugger(self.console)
        self.parser = StatementParser()
        self.searcher = Searcher()
        
    def _get_last_line_indent(self, content: str) -> str:
        """Extract indentation from the last non-empty line."""
        lines = content.splitlines()
        for line in reversed(lines):
            if line.strip():
                return self.searcher.get_indentation(line)
        return ""

    def _validate_operation(self, mod: TextChange) -> Tuple[bool, Optional[str]]:
        """Validate text operation type and parameters
        Returns (is_valid, error_message)"""
        if mod.is_append:
            if not mod.replace_content:
                return False, "Append operation requires content"
            return True, None

        # For delete operations
        if mod.is_delete:
            if not mod.search_content:
                return False, "Delete operation requires search content"
            return True, None

        # For replace operations
        if not mod.search_content:
            return False, "Replace operation requires search content"
        if mod.replace_content is None:
            return False, "Replace operation requires replacement content"

        return True, None

    def apply_modifications(self, content: str, changes: List[TextChange], target_path: Path, debug: bool) -> Tuple[bool, str, Optional[str]]:
        """Apply text modifications to content"""
        modified = content
        any_changes = False
        target_path = target_path.resolve()
        file_ext = target_path.suffix  # Get file extension including the dot

        for mod in changes:
            # Validate operation
            is_valid, error = self._validate_operation(mod)
            if not is_valid:
                return False, content, f"Invalid text operation for {target_path}: {error}"

            try:
                # Handle append operations
                if not mod.search_content:
                    if mod.replace_content:
                        modified = self._append_content(modified, mod.replace_content)
                        any_changes = True
                    continue

                # Handle delete operations (either explicit or via empty replacement)
                if mod.is_delete or (mod.replace_content == "" and mod.search_content):
                    replacer = SearchReplacer(modified, mod.search_content, "", file_ext, debug=debug)
                    modified = replacer.replace()
                    any_changes = True
                    continue

                # Handle search and replace
                replacer = SearchReplacer(modified, mod.search_content, mod.replace_content, file_ext, debug=debug)
                modified = replacer.replace()
                any_changes = True

            except PatternNotFoundException:
                if config.debug:
                    self.debug_failed_finds(mod.search_content, modified, str(target_path))
                return False, content, self._handle_failed_search(target_path, mod.search_content, modified)
    
        return (True, modified, None) if any_changes else (False, content, "No changes were applied")

    def _append_content(self, content: str, new_content: str) -> str:
        """Append content with proper indentation matching."""
        if not content.endswith('\n'):
            content += '\n'
        
        # Add empty line if the last line is not empty
        if content.rstrip('\n').splitlines()[-1].strip():
            content += '\n'
            
        # Get base indentation from last non-empty line
        base_indent = self._get_last_line_indent(content)
        
        # Get the first non-empty line from new content to calculate relative indentation
        first_line, _ = self.searcher.get_first_non_empty_line(new_content)
        if first_line:
            # Calculate indentation adjustments
            new_base_indent = self.searcher.get_indentation(first_line)
            
            # Calculate the shift needed if we're going into negative indentation
            indent_delta = len(base_indent) + (len(new_base_indent) - len(new_base_indent))
            left_shift = abs(min(0, indent_delta))
            
            # Process each line of new content
            result_lines = []
            for line in new_content.splitlines():
                if not line.strip():
                    result_lines.append('')
                    continue
                    
                # Calculate relative indentation considering the left shift
                line_indent = self.searcher.get_indentation(line)
                rel_indent = len(line_indent) - len(new_base_indent)
                # First apply relative indent, then remove left shift if needed
                final_indent_len = max(0, len(line_indent) - left_shift + (len(base_indent) - len(new_base_indent)))
                final_indent = ' ' * final_indent_len
                result_lines.append(final_indent + line.lstrip())
                
            new_content = '\n'.join(result_lines)
            
        return content + new_content

    def _handle_failed_search(self, filepath: Path, search_text: str, content: str) -> str:
        """Handle failed search by logging debug info in a test case format"""
        failed_file = config.workdir / '.janito' / 'change_history' / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_changes_failed.txt"
        failed_file.parent.mkdir(parents=True, exist_ok=True)

        # Create test case format debug info
        debug_info = f"""Test: Failed search in {filepath.name}
========================================
Original:
{content}
========================================
Search pattern:
{search_text}
========================================"""

        failed_file.write_text(debug_info)

        self.console.print(f"\n[red]Failed search saved to: {failed_file}[/red]")
        self.console.print("[yellow]Run with 'python -m janito.search_replace {failed_file}' to debug[/yellow]")

        return f"Could not find search text in {filepath}"

    def debug_failed_finds(self, search_content: str, file_content: str, filepath: str) -> None:
        """Debug find operations without applying changes"""
        if not search_content or not file_content:
            self.console.print("[yellow]Missing search or file content for debugging[/yellow]")
            return

        self.console.print(f"\n[cyan]Debugging finds for {filepath}:[/cyan]")
        self.debugger.debug_find(file_content, search_content)

    def extract_debug_info(self, content: str) -> tuple[Optional[str], Optional[str], Optional[str]]:
        """Extract search text and file content from failed change debug info"""
        try:
            statements = self.parser.parse(content)
            if not statements or statements[0].name != "Failed Find Debug":
                raise ValueError("Not a valid failed find debug file")

            params = statements[0].parameters
            filepath = params.get("filepath")
            search_content = params.get("search", "").strip()
            file_content = params.get("content", "").strip()

            if not all([filepath, search_content, file_content]):
                raise ValueError("Missing required sections in debug file")

            return filepath, search_content, file_content

        except Exception as e:
            self.console.print(f"[red]Error parsing debug info: {e}[/red]")
            return None, None, None