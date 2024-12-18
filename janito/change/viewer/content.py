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

def create_content_preview(filepath: Path, content: str, is_new: bool = False) -> Panel:
    """Create a preview panel with syntax highlighting and metadata"""
    syntax_type = get_file_syntax(filepath)
    file_size = len(content.encode('utf-8'))
    line_count = len(content.splitlines())

    # Format file metadata
    size_str = f"{file_size:,} bytes"
    stats = f"[dim]{line_count:,} lines | {size_str}[/dim]"

    if syntax_type:
        # Use syntax highlighting for known file types
        syntax = Syntax(
            content,
            syntax_type,
            theme="monokai",
            line_numbers=True,
            word_wrap=True,
            code_width=100,
            tab_size=4
        )
        preview = syntax
        file_type = f"[blue]{syntax_type}[/blue]"
    else:
        # Fallback to plain text for unknown types
        preview = content
        file_type = "[yellow]plain text[/yellow]"

    # Adjust title based on whether it's a new file
    title_prefix = "[green]New File[/green]: " if is_new else "Content Preview: "
    title = f"{title_prefix}[green]{filepath.name}[/green] ({file_type})"

    return Panel(
        preview,
        title=title,
        title_align="left",
        subtitle=stats,
        subtitle_align="right",
        border_style="green" if is_new else "cyan",
        padding=(1, 2)
    )