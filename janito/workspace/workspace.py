from pathlib import Path
from typing import List, Set, Dict, Optional, Tuple
import time
from rich.console import Console
from janito.config import config
from .types import WorksetContent, FileInfo, ScanPath  # Add ScanPath import

class PathNotRelativeError(Exception):
    """Raised when a path is not relative."""
    pass

class Workspace:
    """Handles workspace scanning and content management."""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self._content = WorksetContent()
            self._initialized = True

    def scan_files(self, paths: List[Path], recursive_paths: Set[Path]) -> None:
        """Scan files from given paths and update content.
        
        Args:
            paths: List of paths to scan
            recursive_paths: Set of paths to scan recursively
        """
        for path in paths:
            if path.is_absolute():
                raise PathNotRelativeError(f"Path must be relative: {path}")
                
        scan_time = time.time()
        
        if config.debug:
            console = Console(stderr=True)
            console.print(f"\n[cyan]Debug: Starting scan of {len(paths)} paths[/cyan]")

        processed_files: Set[Path] = set()
        for path in paths:
            abs_path = config.workspace_dir / path
            if not (config.skip_work and path == Path(".")):
                self._scan_path(abs_path, processed_files, scan_time, recursive_paths)

        self._content.scan_completed = True
        self._content.analyzed = False
        self._content.scanned_paths = set(paths)

    def _scan_path(self, path: Path, processed_files: Set[Path], scan_time: float, 
                  recursive_paths: Set[Path]) -> None:
        """Scan a single path and process its contents."""
        if path in processed_files:
            return

        # Convert recursive_paths to absolute for comparison
        abs_recursive_paths = {config.workspace_dir / p for p in recursive_paths}

        path = path.resolve()
        processed_files.add(path)

        if path.is_dir():
            try:
                for item in path.iterdir():
                    if item.name.startswith(('.', '__pycache__')):
                        continue
                    if path in abs_recursive_paths:
                        self._scan_path(item, processed_files, scan_time, recursive_paths)
                    elif item.is_file():
                        self._scan_path(item, processed_files, scan_time, recursive_paths)
            except PermissionError:
                if config.debug:
                    Console(stderr=True).print(f"[red]Debug: Permission denied: {path}[/red]")
        elif path.is_file():
            self._process_file(path, scan_time)

    def _process_file(self, path: Path, scan_time: float) -> None:
        """Process a single file and add it to the content."""
        try:
            # Check if file has supported extension or no extension
            supported_extensions = {
            '.py', '.md', '.txt', '.json', '.yaml', '.yml', '.toml',
            '.html', '.htm', '.css', '.js'
            }
            if path.suffix.lower() in supported_extensions or not path.suffix:
                content = path.read_text(encoding='utf-8')
                rel_path = path.relative_to(config.workspace_dir)
                seconds_ago = int(scan_time - path.stat().st_mtime)
                
                file_info = FileInfo(
                    name=str(rel_path),
                    content=content,
                    seconds_ago=seconds_ago
                )
                self._content.add_file(file_info)
                
                if config.debug:
                    Console(stderr=True).print(f"[cyan]Debug: Added file: {rel_path}[/cyan]")
        except (UnicodeDecodeError, PermissionError) as e:
            if config.debug:
                Console(stderr=True).print(f"[red]Debug: Error reading file {path}: {str(e)}[/red]")

    def get_file_info(self, time_ranges: Optional[List[int]] = None) -> Tuple[List[FileInfo], List[FileInfo], List[FileInfo], List[FileInfo]]:
        """Get file information grouped by modification time."""
        return self._content.get_file_info(time_ranges)

    def clear(self) -> None:
        """Clear all workspace content and settings."""
        self._content = WorksetContent()

    @property
    def content(self) -> WorksetContent:
        """Get the workspace content."""
        return self._content
