from typing import Tuple, List, Optional
from rich.console import Console
from pathlib import Path
from datetime import datetime
from ..parser import TextChange
from janito.config import config
from ...clear_statement_parser.parser import StatementParser
from ...text_finder.finder import FindReplacer, PatternNotFoundException

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
        file_ext = target_path.suffix  # No longer need to strip the dot
        find_replacer = FindReplacer(file_type=file_ext)

        for mod in changes:
            # Validate operation
            is_valid, error = self._validate_operation(mod)
            if not is_valid:
                self.console.print(f"[yellow]Warning: Invalid text operation for {target_path}: {error}[/yellow]")
                continue

            try:
                if mod.is_append:
                    # For append, we'll do a replace at the end of the file
                    modified = find_replacer.replace(modified + "\n", "$", mod.replace_content, debug=debug)
                    any_changes = True
                    continue

                # Handle delete operations (either explicit or via empty replacement)
                if mod.is_delete or (mod.replace_content == "" and mod.search_content):
                    modified = find_replacer.replace(modified, mod.search_content, "", debug=debug)
                    any_changes = True
                    continue

                # Handle regular replace operations
                new_content = find_replacer.replace(modified, mod.search_content, mod.replace_content, debug=debug)
                if new_content != modified:
                    modified = new_content
                    any_changes = True

            except PatternNotFoundException:
                if config.debug:
                    self.debug_failed_finds(mod.search_content, modified, str(target_path))
                warning_msg = self._handle_failed_search(target_path, mod.search_content, modified)
                self.console.print(f"[yellow]Warning: {warning_msg}[/yellow]")
                continue
    
        return (True, modified, None)

    def _handle_failed_search(self, filepath: Path, search_text: str, content: str) -> str:
        """Handle failed search by logging debug info in a test case format"""
        failed_file = config.workspace_dir / '.janito' / 'change_history' / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_changes_failed.txt"
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

        self.console.print(f"[yellow]Changes failed saved to: {failed_file}[/yellow]")
        self.console.print("[yellow]Run with 'python -m janito.search_replace {failed_file}' to debug[/yellow]")

        return f"Could not apply change to {filepath} - pattern not found"

    def debug_failed_finds(self, search_content: str, file_content: str, filepath: str) -> None:
        """Debug find operations without applying changes"""
        if not search_content or not file_content:
            self.console.print("[yellow]Missing search or file content for debugging[/yellow]")
            return

        self.console.print(f"\n[cyan]Debugging finds for {filepath}:[/cyan]")
        self.debugger.debug_find(file_content, search_content)

    def extract_debug_info(self, content: str) -> tuple[Optional[str], Optional[str], Optional[str]]:
        """Extract search text and file content from failed change debug info.
        
        Only matches section markers ("========================================")
        when they appear alone on a line.
        """
        try:
            marker = "=" * 40
            lines = content.splitlines()
            section_starts = [i for i, line in enumerate(lines) if line.strip() == marker]
            
            if len(section_starts) < 3:
                raise ValueError("Missing section markers in debug file")
                
            # Extract content between markers
            original_start = section_starts[0] + 2  # +1 for section header, +1 for marker
            search_start = section_starts[1] + 2
            original_content = "\n".join(lines[original_start:section_starts[1]])
            search_content = "\n".join(lines[search_start:section_starts[2]])

            # Extract filename from first line
            if not lines[0].startswith("Test: Failed search in "):
                raise ValueError("Invalid debug file format")
            filepath = lines[0].replace("Test: Failed search in ", "").strip()

            if not all([filepath, search_content, original_content]):
                raise ValueError("Missing required sections in debug file")

            return filepath, search_content, original_content

        except Exception as e:
            self.console.print(f"[red]Error parsing debug info: {e}[/red]")
            return None, None, None