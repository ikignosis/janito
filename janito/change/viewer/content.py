from typing import Optional, Tuple
from pathlib import Path
from rich.syntax import Syntax
from rich.panel import Panel
from .headers import create_progress_header
from rich.rule import Rule


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
        '.cpp': 'cpp',
        '.c': 'c',
        '.h': 'cpp',
        '.hpp': 'cpp',
        '.java': 'java',
        '.go': 'go',
        '.rs': 'rust',
    }
    return ext_map.get(filepath.suffix.lower())

def create_content_preview(filepath: Path, content: str, is_new: bool = False) -> Tuple[Rule, Syntax]:
    """Create a preview with header and syntax highlighting using consistent styling

    Args:
        filepath: Path to the file being previewed
        content: Content to preview
        is_new: Whether this is a new file preview

    Returns:
        Tuple of (header rule, syntax highlighted content)
    """
    # Get file info
    syntax_type = get_file_syntax(filepath)

    # Create header using same style as progress header
    operation = "Create" if is_new else "Preview"
    header_text, style = create_progress_header(
        operation=operation,
        filename=str(filepath.name),
        current=1,
        total=1,
        style="green" if is_new else "cyan"
    )
    header = Rule(header_text, style=style, align="center")

    # Create syntax highlighted content with rule header
    syntax = Syntax(
        content,
        syntax_type or "text",
        theme="monokai",
        line_numbers=True,
        word_wrap=True,
        tab_size=4
    )

    return Rule(header.plain, style="cyan"), syntax
