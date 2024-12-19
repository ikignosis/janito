from pathlib import Path
from typing import List
from rich.console import Console
from .workset import Workset

def preview_scan(paths: List[Path] = None) -> None:
    """Preview what files and directories would be scanned."""
    workset = Workset()
    scan_paths = paths if paths is not None else workset.get_scan_paths()
    _, file_items, skipped_files, ignored_items = workset._scan_paths(scan_paths)
    
    console = Console()
    sections = _create_preview_sections(paths, file_items, skipped_files, ignored_items)
    
    console.print("\n")
    for section in sections:
        console.print(section)
        console.print("\n")

def is_dir_empty(path: Path) -> bool:
    # ...existing code...
    pass