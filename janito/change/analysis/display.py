"""Display formatting for analysis results."""

import re
import sys
from typing import Optional, Dict
from pathlib import Path
from datetime import datetime, timezone
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text
from rich import box
from rich.columns import Columns
from rich.rule import Rule
from janito.agents import agent
from janito.config import config
from .options import AnalysisOption, parse_analysis_options

MIN_PANEL_WIDTH = 40

def get_analysis_summary(options: Dict[str, AnalysisOption]) -> str:
    """Generate a summary of affected directories and their file counts."""
    dirs_summary = {}
    for _, option in options.items():
        for file in option.affected_files:
            clean_path = option.get_clean_path(file)
            dir_path = str(Path(clean_path).parent)
            dirs_summary[dir_path] = dirs_summary.get(dir_path, 0) + 1
    
    return " | ".join([f"{dir}: {count} files" for dir, count in dirs_summary.items()])

def _display_options(options: Dict[str, AnalysisOption]) -> None:
    """Display available options with files organized in columns."""
    console = Console()

    console.print()
    console.print(Rule(" Available Options ", style="bold cyan", align="center"))
    console.print()

    term_width = console.width or 100
    spacing = 4
    total_spacing = spacing * (len(options) - 1)
    panel_width = max(MIN_PANEL_WIDTH, (term_width - total_spacing) // len(options))

    panels = []
    for letter, option in options.items():
        content = Text()

        # Description section
        content.append(Text("Description:\n", style="bold cyan"))
        for item in option.description_items:
            content.append(Text(f"• {item}\n", style="white"))
        content.append(Text("\n"))

        if option.affected_files:
            # Group and display files by type
            file_groups = {
                'Modified': {'files': [], 'style': 'yellow'},
                'New': {'files': [], 'style': 'green'},
                'Deleted': {'files': [], 'style': 'red'}
            }

            # Sort files into groups
            for file in option.affected_files:
                clean_path = file.split(' (')[0]
                if '(new)' in file:
                    file_groups['New']['files'].append(clean_path)
                elif '(removed)' in file:
                    file_groups['Deleted']['files'].append(clean_path)
                else:
                    file_groups['Modified']['files'].append(clean_path)

            # Display each group with header
            for group_name, group_info in file_groups.items():
                if group_info['files']:
                    content.append(Text(f"\n─── {group_name} ───\n", style="cyan"))
                    prev_path = None
                    max_path_len = max(len(str(Path(f).parent)) for f in group_info['files'])
                    for file_path in group_info['files']:
                        path = Path(file_path)
                        curr_path = str(path.parent)
                        if prev_path and curr_path == prev_path:
                            pad_left = (max_path_len - 3) // 2
                            pad_right = max_path_len - 3 - pad_left
                            display_path = " " * pad_left + "..." + " " * pad_right
                        else:
                            display_path = curr_path + " " * (max_path_len - len(curr_path))
                        new_dir = option.is_new_directory(file_path)
                        dir_marker = " [+dir]" if new_dir else ""
                        content.append(Text(f"• {display_path}{dir_marker}/{path.name}\n", style=group_info['style']))
                        prev_path = curr_path

        panel = Panel(
            content,
            box=box.ROUNDED,
            border_style="cyan",
            title=f"Option {letter}: {option.summary}",
            title_align="center",
            padding=(1, 2),
            width=panel_width
        )
        panels.append(panel)

    if panels:
        columns = Columns(
            panels,
            align="center",
            expand=True,
            equal=True,
            padding=(0, spacing // 2)
        )
        console.print(columns)

def _display_markdown(content: str) -> None:
    """Display content in markdown format."""
    console = Console()
    md = Markdown(content)
    console.print(md)

def _display_raw_history() -> None:
    """Display raw message history from Claude agent."""
    console = Console()
    console.print("\n=== Message History ===")
    for role, content in agent.messages_history:
        console.print(f"\n[bold cyan]{role.upper()}:[/bold cyan]")
        console.print(content)
    console.print("\n=== End Message History ===\n")

def format_analysis(analysis: str, raw: bool = False,) -> None:
    """Format and display the analysis output with enhanced capabilities."""
    console = Console()
    
    if raw and agent:
        _display_raw_history(agent)
        return
        
    options = parse_analysis_options(analysis)
    if options:
        _display_options(options)
    else:
        console.print("\n[yellow]Warning: No valid options found in response. Displaying as markdown.[/yellow]\n")
        _display_markdown(analysis)