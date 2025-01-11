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

    def debug_find(self, content: str, start_context: str, end_context: str) -> List[int]:
        """Debug find operation by showing numbered matches between contexts"""
        self.find_count += 1
        matches = []

        # Show search patterns
        self.console.print(f"\n[cyan]Find #{self.find_count} context patterns:[/cyan]")
        self.console.print("[cyan]Start context:[/cyan]")
        for i, line in enumerate(start_context.splitlines()):
            self.console.print(f"[dim]{i+1:3d} | {self._visualize_whitespace(line)}[/dim]")
        
        self.console.print("[cyan]End context:[/cyan]")
        for i, line in enumerate(end_context.splitlines()):
            self.console.print(f"[dim]{i+1:3d} | {self._visualize_whitespace(line)}[/dim]")

        # Process content line by line to find matches
        lines = content.splitlines()
        start_found = False
        for i, line in enumerate(lines):
            if not start_found and start_context.strip() in line.strip():
                start_found = True
                matches.append(i + 1)
                self.console.print(f"[green]Start match at line {i+1}:[/green] {self._visualize_whitespace(line)}")
            elif start_found and end_context.strip() in line.strip():
                matches.append(i + 1)
                self.console.print(f"[green]End match at line {i+1}:[/green] {self._visualize_whitespace(line)}")
                break

        if not matches:
            self.console.print("[yellow]No complete matches found[/yellow]")

        return matches

class TextChangeApplier:
    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()
        self.debugger = TextFindDebugger(self.console)
        self.parser = StatementParser()
        
    def _validate_operation(self, mod: TextChange) -> Tuple[bool, Optional[str]]:
        """Validate text operation type and parameters
        Returns (is_valid, error_message)"""
        if not mod.start_context:
            return False, "Operation requires start_context"
        if not mod.end_context:
            return False, "Operation requires end_context"

        # For replace operations
        if not mod.is_delete and mod.replace_content is None:
            return False, "Replace operation requires replacement content"

        return True, None

    def apply_modifications(self, content: str, changes: List[TextChange], target_path: Path, debug: bool) -> Tuple[bool, str, Optional[str]]:
        """Apply text modifications to content"""
        modified = content
        any_changes = False
        target_path = target_path.resolve()
        file_ext = target_path.suffix
        find_replacer = FindReplacer(file_type=file_ext)

        for mod in changes:
            # Validate operation
            is_valid, error = self._validate_operation(mod)
            if not is_valid:
                self.console.print(f"[yellow]Warning: Invalid text operation for {target_path}: {error}[/yellow]")
                continue

            try:
                # Find content between contexts
                pattern = find_replacer.create_pattern_between_contexts(mod.start_context, mod.end_context)
                
                if mod.is_delete:
                    modified = find_replacer.replace(modified, pattern, "", debug=debug)
                else:
                    modified = find_replacer.replace(modified, pattern, mod.replace_content, debug=debug)
                any_changes = True

            except PatternNotFoundException:
                if config.debug:
                    self.debug_failed_finds(mod.start_context, mod.end_context, modified, str(target_path))
                warning_msg = self._handle_failed_search(target_path, mod.start_context, mod.end_context, modified)
                self.console.print(f"[yellow]Warning: {warning_msg}[/yellow]")
                continue
    
        return (True, modified, None)

    def _handle_failed_search(self, filepath: Path, start_context: str, end_context: str, content: str) -> str:
        """Handle failed search by logging debug info in a test case format"""
        failed_file = config.workspace_dir / '.janito' / 'change_history' / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_changes_failed.txt"
        failed_file.parent.mkdir(parents=True, exist_ok=True)

        debug_info = f"""Test: Failed search in {filepath.name}
========================================
Original:
{content}
========================================
Start context:
{start_context}
========================================
End context:
{end_context}
========================================"""

        failed_file.write_text(debug_info, encoding='utf-8')

        self.console.print(f"[yellow]Changes failed saved to: {failed_file}[/yellow]")
        self.console.print("[yellow]Run with 'python -m janito.search_replace {failed_file}' to debug[/yellow]")

        return f"Could not apply change to {filepath} - pattern not found"

    def debug_failed_finds(self, start_context: str, end_context: str, file_content: str, filepath: str) -> None:
        """Debug find operations without applying changes"""
        if not start_context or not end_context or not file_content:
            self.console.print("[yellow]Missing context or file content for debugging[/yellow]")
            return

        self.console.print(f"\n[cyan]Debugging finds for {filepath}:[/cyan]")
        self.debugger.debug_find(file_content, start_context, end_context)

    def extract_debug_info(self, content: str) -> tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
        """Extract contexts and file content from failed change debug info."""
        try:
            marker = "=" * 40
            lines = content.splitlines()
            section_starts = [i for i, line in enumerate(lines) if line.strip() == marker]
            
            if len(section_starts) < 4:
                raise ValueError("Missing section markers in debug file")
                
            # Extract content between markers
            original_start = section_starts[0] + 2
            start_context_start = section_starts[1] + 2
            end_context_start = section_starts[2] + 2
            
            original_content = "\n".join(lines[original_start:section_starts[1]])
            start_context = "\n".join(lines[start_context_start:section_starts[2]])
            end_context = "\n".join(lines[end_context_start:section_starts[3]])

            # Extract filename from first line
            if not lines[0].startswith("Test: Failed search in "):
                raise ValueError("Invalid debug file format")
            filepath = lines[0].replace("Test: Failed search in ", "").strip()

            if not all([filepath, start_context, end_context, original_content]):
                raise ValueError("Missing required sections in debug file")

            return filepath, start_context, end_context, original_content

        except Exception as e:
            self.console.print(f"[red]Error parsing debug info: {e}[/red]")
            return None, None, None, None