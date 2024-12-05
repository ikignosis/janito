from pathlib import Path
from typing import List, Tuple
from rich.console import Console
from rich.columns import Columns
from janito.config import config
from pathspec import PathSpec
from pathspec.patterns import GitWildMatchPattern


SPECIAL_FILES = ["README.md", "__init__.py", "__main__.py"]

def _scan_paths(paths: List[Path], workdir: Path = None) -> Tuple[List[str], List[str]]:
    """Common scanning logic used by both preview and content collection"""
    content_parts = []
    file_items = []
    skipped_files = []
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

        relative_base = workdir
        if path.is_dir():
            relative_path = path.relative_to(relative_base)
            content_parts.append(f'<directory><path>{relative_path}</path>not sent</directory>')
            file_items.append(f"[blue]•[/blue] {relative_path}/")
            # Check for special files
            special_found = []
            for special_file in SPECIAL_FILES:
                if (path / special_file).exists():
                    special_found.append(special_file)
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
                scan_path(item, level+1)

        else:
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
    
    return "\n".join(content_parts)

def preview_scan(paths: List[Path], workdir: Path = None) -> None:
    """Preview what files and directories would be scanned"""
    console = Console()
    _, file_items = _scan_paths(paths, workdir)
    
    # Change message based on whether we're scanning included paths or workdir
    if len(paths) == 1 and paths[0] == workdir:
        console.print(f"\n[bold blue]Scanning working directory:[/bold blue] {workdir.absolute()}")
    else:
        console.print(f"\n[bold blue]Working directory:[/bold blue] {workdir.absolute()}")
        console.print("\n[bold blue]Scanning included paths:[/bold blue]")
        for path in paths:
            console.print(f"  • {path.absolute()}")
            
    console.print("\n[bold blue]Files that would be analyzed:[/bold blue]")
    console.print(Columns(file_items, padding=(0, 4), expand=True))

def is_dir_empty(path: Path) -> bool:
    """Check if directory is empty, ignoring hidden files"""
    return not any(item for item in path.iterdir() if not item.name.startswith('.'))