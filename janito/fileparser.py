from pathlib import Path
from typing import Dict, Tuple, List, Optional
from dataclasses import dataclass
import re
import ast
from rich.console import Console

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
            # Match search/replace blocks with description
            (r'## ' + re.escape(uuid) + r' search/replace "(.*?)" ##\n?(.*?)## ' + 
             re.escape(uuid) + r' replace with ##\n?(.*?)(?=##|$)', False),
            # Match search/delete blocks with description
            (r'## ' + re.escape(uuid) + r' search/delete "(.*?)" ##\n?(.*?)(?=##|$)', True)
        ]
        
        for pattern, is_delete in block_patterns:
            for block_match in re.finditer(pattern, content, re.DOTALL):
                if is_delete:
                    description, search = block_match.groups()
                    search = search.rstrip('\n') + '\n'  # Ensure single trailing newline
                    replace = None
                else:
                    description, search, replace = block_match.groups()
                    search = search.rstrip('\n') + '\n'  # Ensure single trailing newline
                    replace = (replace.rstrip('\n') + '\n') if replace else None
                    
                search_blocks.append((search, replace, description))
        
        changes[path] = FileChange(
            description=description,
            is_new_file=False,
            search_blocks=search_blocks
        )
        
    return changes