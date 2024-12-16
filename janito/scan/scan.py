from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set, Tuple

from pathspec import PathSpec
from pathspec.patterns import GitWildMatchPattern
from rich.columns import Columns
from rich.console import Console
from rich.panel import Panel

from janito.config import config


SPECIAL_FILES = ["README.md", "__init__.py", "__main__.py"]

def _format_size(size_bytes: int) -> str:
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            break
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} {unit}"

def _get_gitignore_spec() -> PathSpec:
    """Load gitignore patterns if available"""
    gitignore_path = config.workdir / '.gitignore' if config.workdir else None
    if gitignore_path and gitignore_path.exists():
        with open(gitignore_path) as f:
            return PathSpec.from_lines(GitWildMatchPattern, f.read().splitlines())
    return None

def _process_file(path: Path, relative_base: Path) -> Tuple[str, str, bool]:
    """Process a single file and return its XML content, display item and success status"""
    relative_path = path.relative_to(relative_base)
    try:
        # Skip binary files
        if path.read_bytes().find(b'\x00') != -1:
            return "", "", False

        file_content = path.read_text(encoding='utf-8')
        xml_content = f"<file>\n<path>{relative_path}</path>\n<content>\n{file_content}\n</content>\n</file>"
        display_item = f"[cyan]•[/cyan] {relative_path}"
        return xml_content, display_item, True
    except UnicodeDecodeError:
        return "", str(relative_path), False

def _scan_paths(paths: List[Path] = None) -> Tuple[List[str], List[str]]:
    """Common scanning logic for both preview and content collection"""
    content_parts = []
    file_items = []
    skipped_files = []
    processed_files: Set[Path] = set()
    console = Console()
    gitignore_spec = _get_gitignore_spec()

    def scan_path(path: Path, depth: int) -> None:
        if depth > 1 and not config.recursive:
            return

        path = path.resolve()
        if '.janito' in path.parts or '.git' in path.parts or '.pytest_cache' in path.parts:
            return

        relative_base = config.workdir
        if path.is_dir():
            relative_path = path.relative_to(relative_base)
            content_parts.append(f'<directory><path>{relative_path}</path>not sent</directory>')
            file_items.append(f"[blue]•[/blue] {relative_path}/")

            # Process special files
            special_found = []
            for special_file in SPECIAL_FILES:
                special_path = path / special_file
                if special_path.exists() and special_path.resolve() not in processed_files:
                    special_found.append(special_file)
                    processed_files.add(special_path.resolve())
                    xml_content, _, success = _process_file(special_path, relative_base)
                    if success:
                        content_parts.append(xml_content)
                    else:
                        skipped_files.append(str(special_path.relative_to(relative_base)))

            if special_found:
                file_items[-1] = f"[blue]•[/blue] {relative_path}/ [cyan]({', '.join(special_found)})[/cyan]"

            for item in path.iterdir():
                if gitignore_spec and gitignore_spec.match_file(str(item.relative_to(config.workdir))):
                    continue
                if item.resolve() not in processed_files:
                    scan_path(item, depth+1)
        else:
            if path.resolve() in processed_files:
                return

            processed_files.add(path.resolve())
            xml_content, display_item, success = _process_file(path, relative_base)
            if success:
                content_parts.append(xml_content)
                file_items.append(display_item)
            else:
                skipped_files.append(display_item)
                if display_item:
                    console.print(f"[yellow]Warning: Skipping file due to encoding issues: {display_item}[/yellow]")

    for path in paths:
        scan_path(path, 0)

    if skipped_files and config.verbose:
        console.print("\n[yellow]Files skipped due to encoding issues:[/yellow]")
        for file in skipped_files:
            console.print(f"  • {file}")

    return content_parts, file_items

def collect_files_content(paths: List[Path] = None) -> str:
    """Collect content from all files in XML format"""
    console = Console()
    content_parts, file_items = _scan_paths(paths)

    if file_items and config.verbose:
        console.print("\n[bold blue]Contents being analyzed:[/bold blue]")
        console.print(Columns(file_items, padding=(0, 4), expand=True))

    return "\n".join(content_parts)

def preview_scan(paths: List[Path] = None) -> None:
    """Preview what files and directories would be scanned"""
    console = Console()
    _, file_items = _scan_paths(paths)

    console.print("\n[bold blue]Analysis Paths:[/bold blue]")
    console.print(f"[cyan]Working Directory:[/cyan] {config.workdir.absolute()}")
    console.print(f"[cyan]Recursive Mode:[/cyan] {'Enabled' if config.recursive else 'Disabled'}")

    is_workdir_scanned = any(p.resolve() == config.workdir.resolve() for p in paths)
    if len(paths) > (1 if is_workdir_scanned else 0):
        console.print("\n[cyan]Additional Included Paths:[/cyan]")
        for path in paths:
            if path.resolve() != config.workdir.resolve():
                try:
                    rel_path = path.relative_to(config.workdir)
                    console.print(f"  • ./{rel_path}")
                except ValueError:
                    console.print(f"  • {path.absolute()}")

    console.print("\n[bold blue]Files that will be analyzed:[/bold blue]")
    console.print(Columns(file_items, padding=(0, 4), expand=True))


def is_dir_empty(path: Path) -> bool:
    """
    Check if directory is empty (ignoring hidden files/directories).
    
    Args:
        path: Directory path to check
        
    Returns:
        True if directory has no visible files/directories, False otherwise
    """
    if not path.is_dir():
        return False
        
    # List all non-hidden files and directories
    visible_items = [item for item in path.iterdir() 
                    if not item.name.startswith('.')]
    
    return len(visible_items) == 0