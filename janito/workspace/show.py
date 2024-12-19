from rich.traceback import install
install(show_locals=False)

from pathlib import Path
from typing import List, Set
from rich.columns import Columns
from rich.console import Console, Group
from rich.panel import Panel
from rich.rule import Rule
from rich.text import Text
from janito.config import config
from .types import FileInfo, ScanPath
from .stats import collect_file_stats, _format_size 


def show_workset_analysis(
    files: List[FileInfo],
    scan_paths: List[ScanPath],
    cache_blocks: List[List[FileInfo]] = None
) -> None:
    """Display analysis of workspace content and configuration."""

    console = Console()
    content_sections = []

    # Get statistics
    dir_counts, file_types = collect_file_stats(files)

    # Calculate path stats using relative paths
    paths_stats = []
    total_files = 0
    total_size = 0

  
    # Process all paths uniformly
    for scan_path in sorted(scan_paths, key=lambda p: p.path):

        path = scan_path.path
        is_recursive = scan_path.is_recursive
        path_str = str(path)

        # Calculate stats based on scan type
        if is_recursive:
            path_files = sum(count for d, [count, _] in dir_counts.items()
                           if Path(d) == path or Path(d).is_relative_to(path))
            path_size = sum(size for d, [_, size] in dir_counts.items()
                          if Path(d) == path or Path(d).is_relative_to(path))
        else:
            path_files = dir_counts.get(path_str, [0, 0])[0]
            path_size = dir_counts.get(path_str, [0, 0])[1]

        total_files += path_files
        total_size += path_size

        paths_stats.append(
            f"[bold cyan]{path}[/bold cyan]"
            f"[yellow]{'/**' if is_recursive else '/'}[/yellow] "
            f"[[green]{path_files}[/green] "
            f"{'total ' if is_recursive else ''}file(s), "
            f"[blue]{_format_size(path_size)}[/blue]]"
        )

    # Build sections - Show paths first
    if paths_stats or current_dir_stats:
        content_sections.extend([
            "[bold yellow]📌 Included Paths[/bold yellow]",
            Rule(style="yellow"),
        ])

        # All paths are now handled in the main loop

        content_sections.append(
            Text(" | ").join(Text.from_markup(path) for path in paths_stats)
        )

        # Add total summary if there are multiple paths
        if len(paths_stats) > 1:
            content_sections.extend([
                "",  # Empty line for spacing
                f"[bold yellow]Total:[/bold yellow] [green]{total_files}[/green] files, "
                f"[blue]{_format_size(total_size)}[/blue]"
            ])
        content_sections.append("\n")

    # Then show directory structure if verbose
    if config.verbose:
        dir_stats = [
            f"📁 {directory}/ [{count} file(s), {_format_size(size)}]"
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
        else f"[bold cyan]no ext[/bold cyan] [[green]{count}[/green] file(s)]"
        for ext, count in sorted(file_types.items())
    ]
    content_sections.extend([
        "[bold cyan]📑 File Types[/bold cyan]",
        Rule(style="cyan"),
        Text(" | ").join(Text.from_markup(stat) for stat in type_stats)
    ])

    # Finally show cache blocks if in debug mode
    if config.debug and cache_blocks:
        blocks = cache_blocks
        if any(blocks):
            content_sections.extend([
                "\n",
                "[bold blue]🕒 Cache Blocks[/bold blue]",
                Rule(style="blue"),
            ])
            
            block_names = ["Last 5 minutes", "Last hour", "Last 24 hours", "Older"]
            for name, block in zip(block_names, blocks):
                if block:  # Only show non-empty blocks
                    content_sections.extend([
                        f"\n[bold]{name}[/bold] ({len(block)} files):",
                        Columns([
                            Text.assemble(
                                f"{f.name} - ",
                                (f"{f.content.splitlines()[0][:50]}...", "dim")
                            )
                            for f in block[:5]  # Show first 5 files only
                        ], padding=(0, 2)),
                        "" if block == blocks[-1] else Rule(style="dim")
                    ])

    # Display analysis
    console.print("\n")
    console.print(Panel(
        Group(*content_sections),
        title="[bold blue]Workset Analysis[/bold blue]",
        title_align="center"
    ))