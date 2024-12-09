from pathlib import Path
from typing import List, Tuple, Set
from rich.console import Console
from rich.columns import Columns
from rich.panel import Panel
from janito.config import config
from pathspec import PathSpec
from pathspec.patterns import GitWildMatchPattern
from collections import defaultdict



SPECIAL_FILES = ["README.md", "__init__.py", "__main__.py"]

def _scan_paths(paths: List[Path], workdir: Path = None) -> Tuple[List[str], List[str]]:
    """Common scanning logic used by both preview and content collection"""
    content_parts = []
    file_items = []
    skipped_files = []
    processed_files: Set[Path] = set()  # Track processed files
    console = Console()
    
    # Load gitignore if it exists
    gitignore_path = workdir / '.gitignore' if workdir else None
    gitignore_spec = None
    if (gitignore_path and gitignore_path.exists()):
        with open(gitignore_path) as f:
            gitignore = f.read()
        gitignore_spec = PathSpec.from_lines(GitWildMatchPattern, gitignore.splitlines())
    

    def scan_path(path: Path, level: int) -> None:
        """
        Scan a path and add it to the content_parts list
        level 0 means we are scanning the root directory
        level 1 we provide both directory directory name and file content
        level > 1 we just return
        """
        if level > 1:
            return
        
        path = path.resolve()
        relative_base = workdir
        if path.is_dir():
            relative_path = path.relative_to(relative_base)
            content_parts.append(f'<directory><path>{relative_path}</path>not sent</directory>')
            file_items.append(f"[blue]•[/blue] {relative_path}/")
            # Check for special files
            special_found = []
            for special_file in SPECIAL_FILES:
                special_path = path / special_file
                if special_path.exists() and special_path.resolve() not in processed_files:
                    special_found.append(special_file)
                    processed_files.add(special_path.resolve())
            if special_found:
                file_items[-1] = f"[blue]•[/blue] {relative_path}/ [cyan]({', '.join(special_found)})[/cyan]"
                for special_file in special_found:
                    special_path = path / special_file
                    try:
                        relative_path = special_path.relative_to(relative_base)
                        file_content = special_path.read_text(encoding='utf-8')
                        content_parts.append(f"<file>\n<path>{relative_path}</path>\n<content>\n{file_content}\n</content>\n</file>")
                    except UnicodeDecodeError:
                        skipped_files.append(str(relative_path))
                        console.print(f"[yellow]Warning: Skipping file due to encoding issues: {relative_path}[/yellow]")

            for item in path.iterdir():
                # Skip if matches gitignore patterns
                if gitignore_spec:
                    rel_path = str(item.relative_to(workdir))
                    if gitignore_spec.match_file(rel_path):
                        continue
                if item.resolve() not in processed_files:  # Skip if already processed
                    scan_path(item, level+1)

        else:
            resolved_path = path.resolve()
            if resolved_path in processed_files:  # Skip if already processed
                return
                
            processed_files.add(resolved_path)
            relative_path = path.relative_to(relative_base)
            # check if file is binary
            try:
                if path.is_file() and path.read_bytes().find(b'\x00') != -1:
                    console.print(f"[red]Skipped binary file found: {relative_path}[/red]")
                    return
                file_content = path.read_text(encoding='utf-8')
                content_parts.append(f"<file>\n<path>{relative_path}</path>\n<content>\n{file_content}\n</content>\n</file>")
                file_items.append(f"[cyan]•[/cyan] {relative_path}")
            except UnicodeDecodeError:
                skipped_files.append(str(relative_path))
                console.print(f"[yellow]Warning: Skipping file due to encoding issues: {relative_path}[/yellow]")

    for path in paths:
        scan_path(path, 0)
        
    if skipped_files and config.verbose:
        console.print("\n[yellow]Files skipped due to encoding issues:[/yellow]")
        for file in skipped_files:
            console.print(f"  • {file}")
        
    return content_parts, file_items

def collect_files_content(paths: List[Path], workdir: Path = None) -> str:
    """Collect content from all files in XML format"""
    console = Console()
    content_parts, file_items = _scan_paths(paths, workdir)

    if file_items and config.verbose:
        console.print("\n[bold blue]Contents being analyzed:[/bold blue]")
        console.print(Columns(file_items, padding=(0, 4), expand=True))
        
    if config.verbose:
        for part in content_parts:
            if part.startswith('<file>'):
                # Extract filename from XML content
                path_start = part.find('<path>') + 6
                path_end = part.find('</path>')
                if path_start > 5 and path_end > path_start:
                    filepath = part[path_start:path_end]
                    console.print(f"[dim]Adding content from:[/dim] {filepath}")
    
    return "\n".join(content_parts)


def preview_scan(paths: List[Path], workdir: Path = None) -> None:
    """Preview what files and directories would be scanned"""
    console = Console()
    _, file_items = _scan_paths(paths, workdir)
    
    # Display working directory status
    console.print("\n[bold blue]Analysis Paths:[/bold blue]")
    console.print(f"[cyan]Working Directory:[/cyan] {workdir.absolute()}")
    
    # Show if working directory is being scanned
    is_workdir_scanned = any(p.resolve() == workdir.resolve() for p in paths)
    if is_workdir_scanned:
        console.print("[green]✓ Working directory will be scanned[/green]")
    else:
        console.print("[yellow]! Working directory will not be scanned[/yellow]")
    
    # Show included paths relative to working directory
    if len(paths) > (1 if is_workdir_scanned else 0):
        console.print("\n[cyan]Additional Included Paths:[/cyan]")
        for path in paths:
            if path.resolve() != workdir.resolve():
                try:
                    rel_path = path.relative_to(workdir)
                    console.print(f"  • ./{rel_path}")
                except ValueError:
                    # Path is outside working directory
                    console.print(f"  • {path.absolute()}")
    
    console.print("\n[bold blue]Files that will be analyzed:[/bold blue]")
    console.print(Columns(file_items, padding=(0, 4), expand=True))

def is_dir_empty(path: Path) -> bool:
    """Check if directory is empty, ignoring hidden files"""
    return not any(item for item in path.iterdir() if not item.name.startswith('.'))

def show_content_stats(content: str) -> None:
    if not content:
        return
        
    dir_counts = defaultdict(int)
    for line in content.split('\n'):
        if line.startswith('<path>'):
            path = Path(line.replace('<path>', '').replace('</path>', '').strip())
            dir_counts[str(path.parent)] += 1
    
    console = Console()
    stats = [f"{directory} ({count} files)" for directory, count in dir_counts.items()]
    columns = Columns(stats, equal=True, expand=True)
    panel = Panel(columns, title="Work Context")
    console.print(panel)
