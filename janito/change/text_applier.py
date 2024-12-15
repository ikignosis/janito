from typing import Tuple, List, Optional
from rich.console import Console
from typing import List
from janito.config import config

class TextFindDebugger:
    def __init__(self, console: Console):
        self.console = console
        self.find_count = 0
        
    def debug_find(self, content: str, search: str) -> List[int]:
        """Debug find operation by showing numbered matches with detailed visualization"""
        self.find_count += 1
        matches = []
        
        # Display search block details
        self.console.print(f"\n[cyan]Find #{self.find_count} analysis:[/cyan]")
        self.console.print(f"[cyan]Search pattern ({len(search.splitlines())} lines):[/cyan]")
        
        # Show search pattern with line numbers and whitespace
        search_lines = search.splitlines()
        search_stripped = search.strip()
        for i, line in enumerate(search_lines):
            vis_line = line.replace(' ', '·').replace('\t', '→')
            self.console.print(f"[dim]{i+1:3d} | {vis_line}[/dim]")

        # Show content analysis
        content_lines = content.splitlines()
        self.console.print(f"\n[cyan]Content analysis ({len(content_lines)} lines):[/cyan]")
        
        context_lines = 2  # Number of lines to show before and after match
        
        # Process content line by line
        for i, line in enumerate(content_lines):
            vis_line = line.replace(' ', '·').replace('\t', '→')
            line_stripped = line.strip()
            
            # Check for match
            if search_stripped in line_stripped:
                matches.append(i + 1)
                
                # Show context before match
                start_ctx = max(0, i - context_lines)
                for ctx_i in range(start_ctx, i):
                    ctx_line = content_lines[ctx_i].replace(' ', '·').replace('\t', '→')
                    self.console.print(f"[dim]{ctx_i+1:3d} | {ctx_line}[/dim]")
                
                # Show matching line with position marker
                match_start = line.find(search_stripped)
                self.console.print(f"[green]{i+1:3d} | {vis_line}[/green]")
                marker = ' ' * (match_start + 5) + '^' * len(search_stripped)
                self.console.print(f"     {marker}")
                
                # Show context after match
                end_ctx = min(len(content_lines), i + context_lines + 1)
                for ctx_i in range(i + 1, end_ctx):
                    ctx_line = content_lines[ctx_i].replace(' ', '·').replace('\t', '→')
                    self.console.print(f"[dim]{ctx_i+1:3d} | {ctx_line}[/dim]")
                
                self.console.print("")  # Add spacing between matches
        
        # Show summary and debug info
        if matches:
            self.console.print(f"[green]Found {len(matches)} match(es) at lines: {', '.join(map(str, matches))}[/green]")
        else:
            self.console.print("\n[yellow]No matches found - Debug Information:[/yellow]")
            self.console.print(f"Search (stripped): '{search_stripped}'")
            self.console.print(f"Search length: {len(search_stripped)} characters")
            self.console.print("\nFirst non-matching line comparison:")
            if content_lines:
                first_line = content_lines[0].strip()
                self.console.print(f"First line (stripped): '{first_line}'")
                self.console.print(f"First line length: {len(first_line)} characters")
                self._show_diff_markers(search_stripped, first_line)
            
        return matches
        
    def _show_diff_markers(self, search: str, content: str) -> None:
        """Show character differences between search and content"""
        min_len = min(len(search), len(content))
        diff_pos = []
        
        for i in range(min_len):
            if search[i] != content[i]:
                diff_pos.append(i)
                
        if diff_pos:
            self.console.print("\nFirst difference at position(s):")
            for pos in diff_pos[:3]:  # Show first 3 differences
                self.console.print(f"Position {pos}: '{search[pos]}' vs '{content[pos]}'")

from pathlib import Path
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from .parser import TextChange
from janito.config import config
from ..clear_statement_parser.parser import StatementParser  # Add this import

class TextFindDebugger:
    def __init__(self, console: Console):
        self.console = console
        self.find_count = 0
        
    def debug_find(self, content: str, search: str) -> List[int]:
        """Debug find operation by showing numbered matches with whitespace visualization"""
        self.find_count += 1
        matches = []

        # show the entire search block with proper whitespace visualization
        self.console.print(f"\n[cyan]Find #{self.find_count} search block:[/cyan]")
        search_lines = [line.replace(' ', '·').replace('\t', '→').replace('\n', '↵\n') 
                       for line in search.splitlines()]
        for i, line in enumerate(search_lines):
            self.console.print(f"[dim]{i+1:3d} | {line}[/dim]")
        
        # Convert whitespace to visible characters for content
        vis_content = content.replace(' ', '·').replace('\t', '→').replace('\n', '↵\n')
        
        # Split content into lines
        lines = vis_content.split('\n')
        for i, line in enumerate(lines):
            if search.strip() in line.strip():
                matches.append(i + 1)
                self.console.print(f"[cyan]Find #{self.find_count}[/cyan] matched at line {i + 1}:")
                self.console.print(f"[dim]{line}[/dim]")
        
        if not matches:
            self.console.print(f"[yellow]Find #{self.find_count} failed to match:[/yellow]")
        
            
        return matches

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
            # show search content
            if not mod.search_content:  # Append operation
                if mod.replace_content:
                    if modified and not modified.endswith('\n'):
                        modified += '\n'
                    modified += mod.replace_content
                    any_changes = True
                continue

            if config.debug:  # Use config.debug instead of debug_mode
                matches = self.debugger.debug_find(modified, mod.search_content)
                if not matches:
                    return False, "", f"Search text not found"

            if mod.replace_content is not None:
                # Replace operation
                modified = modified.replace(mod.search_content, mod.replace_content)
                any_changes = True
            else:
                # Delete operation
                modified = modified.replace(mod.search_content, '')
                any_changes = True

        if not any_changes:
            return False, content, "No changes were applied"

        return True, modified, ""

    def _handle_failed_search(self, filepath: Path, search_text: str, content: str) -> str:
        """Handle failed search by logging debug info using clear statement format"""
        failed_file = config.workdir / '.janito' / 'change_history' / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_changes_failed.txt"
        failed_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Prepare multiline text blocks with dots
        search_lines = [f".{line}" for line in search_text.splitlines()]
        content_lines = [f".{line}" for line in content.splitlines()]
        
        # Use clear statement format
        debug_info = f"""Failed Find Debug
    filepath: {filepath}
    search:
{chr(10).join('    ' + line for line in search_lines)}
    content:
{chr(10).join('    ' + line for line in content_lines)}
"""
        failed_file.write_text(debug_info)
        
        # Debug output with line numbers and whitespace visualization
        lines = content.splitlines()
        content_with_ws = '\n'.join(f'{i+1:3d} | {line.replace(" ", "·")}↵'
                                   for i, line in enumerate(lines))
        self.console.print(f"\n[yellow]File content ({len(lines)} lines, with whitespace):[/yellow]")
        self.console.print(Panel(content_with_ws))
        self.console.print(f"\n[red]Failed search saved to: {failed_file}[/red]")
        
        return f"Could not find search text in {filepath}"

    def debug_failed_finds(self, search_content: str, file_content: str, filepath: str) -> None:
        """Debug find operations without applying changes"""
        if not search_content or not file_content:
            self.console.print("[yellow]Missing search or file content for debugging[/yellow]")
            return
            
        self.console.print(f"\n[cyan]Debugging finds for {filepath}:[/cyan]")
        # show file content and search content
        self.console.print(f"[dim]Search Text: {search_content}[/dim]")
        self.debugger.debug_find(file_content, search_content)
        
    def extract_debug_info(self, content: str) -> tuple[Optional[str], Optional[str], Optional[str]]:
        """Extract search text and file content from failed change debug info using clear statement parser"""
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
    def _handle_insert(self, content: str, insert_text: str, position: int) -> Tuple[bool, str, Optional[str]]:
        """Insert text at specified position in content.

        Args:
            content: Original text content
            insert_text: Text to insert
            position: Position to insert at

        Returns:
            Tuple of (success, modified_content, error_message)
        """
        try:
            if position < 0 or position > len(content):
                return False, content, f"Invalid insert position: {position}"

            # Insert the text at specified position
            modified = content[:position] + insert_text + content[position:]
            return True, modified, None

        except Exception as e:
            return False, content, f"Error during insert: {str(e)}"