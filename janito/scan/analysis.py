from collections import defaultdict
from pathlib import Path
from typing import Dict, List

from rich.columns import Columns
from rich.console import Console, Group
from rich.panel import Panel
from rich.rule import Rule

def analyze_workspace_content(content: str) -> None:
    """Show statistics about the scanned content"""
    if not content:
        return

    dir_counts: Dict[str, int] = defaultdict(int)
    dir_sizes: Dict[str, int] = defaultdict(int)
    file_types: Dict[str, int] = defaultdict(int)
    current_path = None
    current_content = []

    for line in content.split('\n'):
        if line.startswith('<path>'):
            path = Path(line.replace('<path>', '').replace('</path>', '').strip())
            current_path = str(path.parent)
            dir_counts[current_path] += 1
            file_types[path.suffix.lower() or 'no_ext'] += 1
        elif line.startswith('<content>'):
            current_content = []
        elif line.startswith('</content>'):
            content_size = sum(len(line.encode('utf-8')) for line in current_content)
            if current_path:
                dir_sizes[current_path] += content_size
            current_content = []
        elif current_content is not None:
            current_content.append(line)

    console = Console()

    # Directory statistics
    dir_stats = [
        f"📁 {directory}/ [{count} file(s), {_format_size(size)}]"
        for directory, (count, size) in (
            (d, (dir_counts[d], dir_sizes[d]))
            for d in sorted(dir_counts.keys())
        )
    ]

    # File type statistics
    type_stats = [
        f"📄 {ext.lstrip('.')} [{count} file(s)]"
        for ext, count in sorted(file_types.items())
    ]

    # Create grouped content with styled separators
    content = Group(
        "\n[bold magenta]📂 Directory Structure[/bold magenta]",
        Rule(style="magenta"),
        Columns(dir_stats, equal=True, expand=True),
        "\n\n[bold cyan]📑 File Types[/bold cyan]",
        Rule(style="cyan"),
        Columns(type_stats, equal=True, expand=True),
        "\n"
    )

    # Display workspace analysis in panel
    console.print("\n")
    console.print(Panel(
        content,
        title="[bold blue]Workspace Analysis[/bold blue]",
        title_align="center"
    ))

def _format_size(size_bytes: int) -> str:
    """Format size in bytes to human readable format"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            break
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} {unit}"