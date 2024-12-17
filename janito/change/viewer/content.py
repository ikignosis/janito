from typing import Optional
from pathlib import Path
from rich.syntax import Syntax
from rich.panel import Panel
from rich.console import Console

def get_file_syntax(filepath: Path) -> Optional[str]:
    """Get syntax lexer name based on file extension"""
    ext_map = {
        '.py': 'python',
        '.js': 'javascript',
        '.ts': 'typescript',
        '.html': 'html',
        '.css': 'css',
        '.json': 'json',
        '.md': 'markdown',
        '.yaml': 'yaml',
        '.yml': 'yaml',
        '.sh': 'bash',
        '.bash': 'bash',
        '.sql': 'sql',
        '.xml': 'xml',
    }
    return ext_map.get(filepath.suffix.lower())

def create_content_preview(filepath: Path, content: str) -> Panel:
    """Create a preview panel with syntax highlighting"""
    syntax_type = get_file_syntax(filepath)

    if syntax_type:
        # Use syntax highlighting for known file types
        syntax = Syntax(
            content,
            syntax_type,
            theme="monokai",
            line_numbers=True,
            word_wrap=True
        )
        preview = syntax
    else:
        # Fallback to plain text for unknown types
        preview = content

    return Panel(
        preview,
        title=f"Content Preview: {filepath.name}",
        title_align="left"
    )