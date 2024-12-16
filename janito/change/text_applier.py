from typing import Tuple, List, Optional
from rich.console import Console
from pathlib import Path
from datetime import datetime
from .parser import TextChange
from janito.config import config
from ..clear_statement_parser.parser import StatementParser
from .search_replace import SearchReplacer, PatternNotFoundException

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

from .operations import TextOperation

class TextChangeApplier:
    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()
        self.debugger = TextFindDebugger(self.console)
        self.parser = StatementParser()

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

    def apply_modifications(self, content: str, changes: List[TextChange], target_path: Path) -> Tuple[bool, str, Optional[str]]:
        """Apply text modifications to content"""
        modified = content
        any_changes = False
        target_path = target_path.resolve()

        for mod in changes:
            # Validate operation
            is_valid, error = self._validate_operation(mod)
            if not is_valid:
                return False, content, f"Invalid operation for {target_path}: {error}"

            try:
                # Handle append operations
                if not mod.search_content:
                    if mod.replace_content:
                        modified = self._append_content(modified, mod.replace_content)
                        any_changes = True
                    continue

                # Handle delete operations
                if mod.is_delete:
                    replacer = SearchReplacer(modified, mod.search_content, "")
                    modified = replacer.replace()
                    any_changes = True
                    continue

                # Handle search and replace
                replacer = SearchReplacer(modified, mod.search_content, mod.replace_content)
                modified = replacer.replace()
                any_changes = True

            except PatternNotFoundException:
                if config.debug:
                    self.debug_failed_finds(mod.search_content, modified, str(target_path))
                return False, content, self._handle_failed_search(target_path, mod.search_content, modified)
            except Exception as e:
                return False, content, f"Error applying changes to {target_path}: {str(e)}"

        return (True, modified, None) if any_changes else (False, content, "No changes were applied")

    def _append_content(self, content: str, new_content: str) -> str:
        """Append content with proper line ending handling"""
        if not content.endswith('\n'):
            content += '\n'
        return content + new_content

    def _handle_failed_search(self, filepath: Path, search_text: str, content: str) -> str:
        """Handle failed search by logging debug info in a test case format"""
        failed_file = config.workdir / '.janito' / 'change_history' / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_changes_failed.txt"
        failed_file.parent.mkdir(parents=True, exist_ok=True)

        # Create test case format debug info - search only
        debug_info = f"""Test: Failed search in {filepath.name}
========================================
Original:
{content}

Search pattern:
{search_text}
========================================"""

        failed_file.write_text(debug_info)

        self.console.print(f"\n[red]Failed search saved to: {failed_file}[/red]")
        
        # Use SearchReplacer's debug_indentation
        replacer = SearchReplacer("", "", "")  # Empty instance for using debug method
        self.console.print("\n[yellow]Indentation Analysis:[/yellow]")
        with self.console.capture() as capture:
            replacer.debug_indentation(content, search_text)
        debug_output = capture.get()
        self.console.print(debug_output)
        
        # Also show whitespace markers for quick visual reference
        self.console.print("\n[yellow]Search pattern (with whitespace markers):[/yellow]")
        for line in search_text.splitlines():
            self.console.print(f"[dim]{self.debugger._visualize_whitespace(line)}[/dim]")
        
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