from pathlib import Path
from typing import Dict, Tuple, List
from dataclasses import dataclass
import re
import ast
from rich.console import Console

@dataclass
class FileChange:
    """Represents a file change with change instructions"""
    description: str
    change_content: List[str]  # Content between the change markers
    is_new_file: bool = False

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
    """Parse file changes from response blocks marked with UUIDs"""
    changes = {}
    file_pattern = r'## ([a-f0-9]{8}) file (.*?) (modify|create) "(.*?)" ##(.*?)## \1 file end ##'
    file_matches = re.finditer(file_pattern, response_text, re.DOTALL)
    
    for match in file_matches:
        uuid, filepath, action, description, content = match.groups()
        path = Path(filepath.strip())
        
        if action == 'create':
            # For new files, each line becomes an addition
            changes[path] = FileChange(
                description=description,
                change_content=[f">{line}" for line in content.strip().split('\n')],
                is_new_file=True
            )
            continue
        
        # For modifications, extract lines between change markers
        change_pattern = rf'## {uuid} change begin ##(.*?)## {uuid} change end ##'
        change_match = re.search(change_pattern, content, re.DOTALL)
        
        if change_match:
            content_lines = []
            change_content = change_match.group(1).strip()
            
            # Capture each line with its prefix intact
            for line in change_content.split('\n'):
                if line.startswith(('=', '>', '<')):
                    content_lines.append(line)
                else:
                    # Handle lines without prefixes (shouldn't happen with correct format)
                    console = Console()
                    console.print(f"[yellow]Warning: Line without prefix in {filepath}: {line}[/yellow]")
            
            changes[path] = FileChange(
                description=description,
                change_content=content_lines,
                is_new_file=False
            )
    
    return changes