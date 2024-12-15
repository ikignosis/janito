from typing import Tuple, List, Optional
from rich.console import Console
from pathlib import Path
from datetime import datetime
from rich.panel import Panel
from .parser import TextChange
from janito.config import config
from ..clear_statement_parser.parser import StatementParser
from .search_replace import smart_search_replace, PatternNotFoundException

class TextFindDebugger:
    def __init__(self, console: Console):
        self.console = console
        self.find_count = 0

    def debug_find(self, content: str, search: str) -> List[int]:
        """Debug find operation by showing numbered matches"""
        self.find_count += 1
        matches = []

        # Show search pattern
        self.console.print(f"\n[cyan]Find #{self.find_count} search pattern:[/cyan]")
        for i, line in enumerate(search.splitlines()):
            self.console.print(f"[dim]{i+1:3d} | {line}[/dim]")

        # Process content line by line
        lines = content.splitlines()
        for i, line in enumerate(lines):
            if search.strip() in line.strip():
                matches.append(i + 1)
                self.console.print(f"[green]Match at line {i+1}[/green]")

        if not matches:
            self.console.print("[yellow]No matches found[/yellow]")

        return matches

def verify_replacement(source: str, replacement: str, modified: str) -> bool:
    """Verify that the replacement text exists in the modified content"""
    replacement_normalized = '\n'.join(line.strip() for line in replacement.splitlines())
    modified_normalized = '\n'.join(line.strip() for line in modified.splitlines())
    return replacement_normalized in modified_normalized

class TextChangeApplier:
    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()
        self.debugger = TextFindDebugger(self.console)
        self.parser = StatementParser()

    def apply_modifications(self, content: str, changes: List[TextChange], filepath: Path) -> Tuple[bool, str, Optional[str]]:
        """Apply text modifications to content
        Returns: (success, modified_content, error_message)"""
        modified = content
        any_changes = False

        for mod in changes:
            try:
                if not mod.search_content:  # Append operation
                    if mod.replace_content:
                        if modified and not modified.endswith('\n'):
                            modified += '\n'
                        modified += mod.replace_content
                        any_changes = True
                    continue

                # Apply the replacement
                new_content = smart_search_replace(modified, mod.search_content, mod.replace_content)

                # Verify the replacement was successful
                if mod.replace_content and not verify_replacement(mod.search_content, mod.replace_content, new_content):
                    return False, content, f"Replacement verification failed"

                modified = new_content
                any_changes = True

            except PatternNotFoundException:
                if config.debug:
                    self.debug_failed_finds(mod.search_content, modified, str(filepath))
                return False, content, self._handle_failed_search(filepath, mod.search_content, modified)

        if not any_changes:
            return False, content, "No changes were applied"

        return True, modified, None

    def _handle_failed_search(self, filepath: Path, search_text: str, content: str) -> str:
        """Handle failed search by logging debug info"""
        failed_file = config.workdir / '.janito' / 'change_history' / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_changes_failed.txt"
        failed_file.parent.mkdir(parents=True, exist_ok=True)

        # Use clear statement format
        debug_info = f"""Failed Find Debug
    filepath: {filepath}
    search:
{chr(10).join('    .' + line for line in search_text.splitlines())}
    content:
{chr(10).join('    .' + line for line in content.splitlines())}
"""
        failed_file.write_text(debug_info)

        self.console.print(f"\n[red]Failed search saved to: {failed_file}[/red]")
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
            if not statements or not statements[0].name == "Failed Find Debug":
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