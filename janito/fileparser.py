from pathlib import Path
from typing import Dict, Tuple, List, Optional
from dataclasses import dataclass
import re
import ast
import sys  # Add this import
from rich.console import Console
from rich.panel import Panel  # Add this import
from janito.config import config  # Add this import

@dataclass
class FileChange:
    """Represents a file change with search/replace, search/delete or create instructions"""
    description: str
    is_new_file: bool
    content: str = ""  # For new files
    search_blocks: List[Tuple[str, Optional[str], Optional[str]]] = None  # (search, replace, description)

    def add_search_block(self, search: str, replace: Optional[str], description: Optional[str] = None) -> None:
        """Add a search/replace or search/delete block with optional description"""
        if self.search_blocks is None:
            self.search_blocks = []
        self.search_blocks.append((search, replace, description))

def validate_python_syntax(content: str, filepath: Path) -> Tuple[bool, str]:
    """Validate Python syntax and return (is_valid, error_message)"""
    try:
        ast.parse(content)
        console = Console()
        console.print(f"[green]✓ Python syntax validation passed:[/green] {filepath.absolute()}")
        return True, ""
    except SyntaxError as e:
        error_msg = f"Line {e.lineno}: {e.msg}"
        console = Console()
        console.print(f"[red]✗ Python syntax validation failed:[/red] {filepath.absolute()}")
        console.print(f"[red]  {error_msg}[/red]")
        return False, error_msg


def parse_block_changes(response_text: str) -> Dict[Path, FileChange]:
    """Parse file changes from response blocks"""
    changes = {}
    console = Console()
    # Match file blocks with UUID
    file_pattern = r'## ([a-f0-9]{8}) file (.*?) (modify|create) "(.*?)" ##\n?(.*?)## \1 file end ##'
    
    for match in re.finditer(file_pattern, response_text, re.DOTALL):
        uuid, filepath, action, description, content = match.groups()
        path = Path(filepath.strip())
        
        if action == 'create':
            changes[path] = FileChange(
                description=description,
                is_new_file=True,
                content=content[1:] if content.startswith('\n') else content,
                search_blocks=[]
            )
            continue
            
        # For modifications, find all search/replace and search/delete blocks
        search_blocks = []
        block_patterns = [
            # Match search/replace blocks with description - updated pattern
            (r'## ' + re.escape(uuid) + r' search/replace "(.*?)" ##\n?(.*?)## ' + 
             re.escape(uuid) + r' replace with ##\n?(.*?)(?=## ' + re.escape(uuid) + r'|$)', False),
            # Match search/delete blocks with description
            (r'## ' + re.escape(uuid) + r' search/delete "(.*?)" ##\n?(.*?)(?=## ' + re.escape(uuid) + r'|$)', True)
        ]
        
        if config.debug:
            console.print("\n[blue]Updated regex patterns:[/blue]")
            for pattern, is_delete in block_patterns:
                console.print(Panel(pattern, title="Search/Replace Pattern" if not is_delete else "Search/Delete Pattern", border_style="blue"))
                
        for pattern, is_delete in block_patterns:
            if config.debug:
                console.print(f"\n[blue]Looking for pattern:[/blue]")
                console.print(Panel(pattern, title="Pattern", border_style="blue"))
                console.print(f"\n[blue]In content:[/blue]")
                console.print(Panel(content, title="Content", border_style="blue"))
                
            for block_match in re.finditer(pattern, content, re.DOTALL):
                if is_delete:
                    description, search = block_match.groups()
                    search = search.rstrip('\n') + '\n'  # Ensure single trailing newline
                    replace = None
                else:
                    description, search, replace = block_match.groups()
                    search = search.rstrip('\n') + '\n'  # Ensure single trailing newline
                    replace = (replace.rstrip('\n') + '\n') if replace else None
                    
                    # Abort parsing if replace content is empty
                    if not is_delete and (replace is None or replace.strip() == ''):
                        console.print(f"\n[red]Error: Empty replace content found![/red]")
                        console.print(f"[red]File:[/red] {filepath}")
                        console.print(f"[red]Description:[/red] {description}")
                        console.print("[yellow]Search block:[/yellow]")
                        console.print(Panel(search, title="Search Content", border_style="yellow"))
                        console.print("[red]Replace block is empty or contains only whitespace![/red]")
                        console.print("[red]Aborting due to empty replace content.[/red]")
                        sys.exit(1)
                    
                    # Enhanced debug info
                    if config.debug or (not is_delete and (replace is None or replace.strip() == '')):
                        console.print(f"\n[yellow]Search/Replace block analysis:[/yellow]")
                        console.print(f"[yellow]File:[/yellow] {filepath}")
                        console.print(f"[yellow]Description:[/yellow] {description}")
                        console.print("[yellow]Search block:[/yellow]")
                        console.print(Panel(search, title="Search Content", border_style="yellow"))
                        console.print("[yellow]Replace block:[/yellow]")
                        console.print(Panel(replace if replace else "<empty>", title="Replace Content", border_style="yellow"))
                        console.print("\n[blue]Match groups:[/blue]")
                        for i, group in enumerate(block_match.groups()):
                            console.print(Panel(str(group), title=f"Group {i}", border_style="blue"))
                    
                search_blocks.append((search, replace, description))
        
        # Add debug info if no blocks were found
        if config.debug and not search_blocks:
            console.print(f"\n[red]No search/replace blocks found for file:[/red] {filepath}")
            console.print("[red]Check if the content format matches the expected patterns[/red]")
        
        changes[path] = FileChange(description=description, is_new_file=False, search_blocks=search_blocks)
    
    return changes