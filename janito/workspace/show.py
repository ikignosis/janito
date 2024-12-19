from collections import defaultdict
from pathlib import Path
from rich.columns import Columns
from rich.console import Console, Group
from rich.panel import Panel
from rich.rule import Rule
from rich.text import Text
from janito.config import config
from .types import WorksetContent

def show_workset_analysis(workset) -> None:
    """Display analysis of current workset content."""
    if not workset.content:
        return

    console = Console()
    content_sections = []

    # Collect statistics
    dir_counts, dir_sizes, file_types, paths_stats, total_summary = _collect_stats(workset)

    # Build sections - Show paths horizontally with /** for recursive
    if paths_stats:
        content_sections.extend([
            "[bold yellow]📌 Included Paths[/bold yellow]",
            Rule(style="yellow"),
            Text(" | ").join(Text.from_markup(path) for path in paths_stats),
        ])
        
        # Add total summary if there are multiple paths
        if len(paths_stats) > 1:
            content_sections.extend([
                "",  # Empty line for spacing
                f"[bold yellow]Total:[/bold yellow] [green]{total_summary['files']}[/green] files, "
                f"[blue]{_format_size(total_summary['size'])}[/blue]"
            ])
        content_sections.append("\n")

    if config.verbose:
        # Convert absolute paths to relative for directory stats
        dir_stats = [
            f"📁 {Path(directory).relative_to(config.workspace_dir)}/ [{count} file(s), {_format_size(size)}]"
            for directory, (count, size) in sorted(dir_counts.items())
        ]
        content_sections.extend([
            "[bold magenta]📂 Directory Structure[/bold magenta]",
            Rule(style="magenta"),
            Columns(dir_stats, equal=True, expand=True),
            "\n"
        ])

    type_stats = [
        f"[bold cyan].{ext.lstrip('.')}[/bold cyan] [[green]{count}[/green] file(s)]" 
        if ext != 'no_ext' 
        else f"[bold cyan]{ext}[/bold cyan] [[green]{count}[/green] file(s)]"
        for ext, count in sorted(file_types.items())
    ]
    content_sections.extend([
        "[bold cyan]📑 File Types[/bold cyan]",
        Rule(style="cyan"),
        Text(" | ").join(Text.from_markup(stat) for stat in type_stats)
    ])

    # Display analysis
    console.print("\n")
    console.print(Panel(
        Group(*content_sections),
        title="[bold blue]Workset Analysis[/bold blue]",
        title_align="center"
    ))

def _collect_stats(workset) -> tuple[dict, dict, dict, list, dict]:
    """Collect statistics from workspace content."""
    dir_counts = defaultdict(lambda: [0, 0])
    file_types = defaultdict(int)
    current_path = None
    current_content = []

    for line in workset.content.split('\n'):
        if line.startswith('<path>'):
            path = Path(line.replace('<path>', '').replace('</path>', '').strip())
            current_path = str(path.parent)
            dir_counts[current_path][0] += 1
            file_types[path.suffix.lower() or 'no_ext'] += 1
        elif line.startswith('<content>'):
            current_content = []
        elif line.startswith('</content>'):
            content_size = sum(len(line.encode('utf-8')) for line in current_content)
            if current_path:
                dir_counts[current_path][1] += content_size
            current_content = []
        elif current_content is not None:
            current_content.append(line)

    # Calculate path stats with updated counting logic
    paths_stats = []
    total_files = 0
    total_size = 0
    scan_paths = workset.get_scan_paths()
    
    for path in sorted(set(scan_paths)):
        base_path = Path(path)
        is_recursive = path in workset.recursive_paths

        if is_recursive:
            # For recursive paths, count all files in subdirectories
            path_files = sum(count for d, [count, _] in dir_counts.items()
                           if Path(d).is_relative_to(base_path))
            path_size = sum(size for d, [_, size] in dir_counts.items()
                          if Path(d).is_relative_to(base_path))
        else:
            # For non-recursive paths, only count files directly in that directory
            path_files = dir_counts[str(base_path)][0] if str(base_path) in dir_counts else 0
            path_size = dir_counts[str(base_path)][1] if str(base_path) in dir_counts else 0

        total_files += path_files
        total_size += path_size
        path_str = str(path.relative_to(config.workspace_dir))
        
        paths_stats.append(
            f"[bold cyan]{path_str}[/bold cyan]"
            f"[yellow]{'/**' if is_recursive else '/'}[/yellow] "
            f"[[green]{path_files}[/green] "
            f"{'total ' if is_recursive else ''}file(s), "
            f"[blue]{_format_size(path_size)}[/blue]]"
        )

    return (
        {k: (v[0], v[1]) for k, v in dir_counts.items()},
        {k: v[1] for k, v in dir_counts.items()},
        file_types,
        paths_stats,
        {'files': total_files, 'size': total_size}  # Add total summary
    )

def _format_size(size_bytes: int) -> str:
    """Format size in bytes to human readable format."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            break
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} {unit}"
