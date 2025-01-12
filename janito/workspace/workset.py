from pathlib import Path
from typing import List, Set, Tuple
from .show import show_workset_analysis
from rich.console import Console
from janito.config import config
from .types import WorksetContent, FileInfo, ScanPath, ScanType
from .workspace import Workspace
from janito.change.preview import setup_preview_directory
import tempfile
import shutil
import pathspec

class PathNotRelativeError(Exception):
    """Raised when a path is not relative."""
    pass

class Workset:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init()
        return cls._instance

    def _init(self):
        self._scan_paths: List[ScanPath] = []
        self._content = WorksetContent()
        self._workspace = Workspace()
        if not config.skip_work:
            self.add_scan_path(Path("."))

    def add_scan_path(self, path: Path, scan_type: ScanType = ScanType.PLAIN) -> None:
        """Add a path with specific scan type.

        Args:
            path: Relative path to add for scanning
            scan_type: Type of scanning (PLAIN or RECURSIVE)

        Raises:
            PathNotRelativeError: If path is absolute
        """
        if path.is_absolute():
            raise PathNotRelativeError(f"Path must be relative: {path}")

        scan_path = ScanPath(path, scan_type)
        ScanPath.validate(path)
        self._scan_paths.append(scan_path)

        if config.debug:
            Console(stderr=True).print(
                f"[cyan]Debug: Added {scan_type.name.lower()} scan path: {path}[/cyan]"
            )

    def refresh(self) -> None:
        """Refresh content by scanning configured paths"""
        self.clear()
        paths = self.get_scan_paths()
        
        if config.debug:
            Console(stderr=True).print(f"[cyan]Debug: Refreshing workset with paths: {paths}[/cyan]")
            
        self._workspace.scan_files(paths, self.get_recursive_paths())
        self._content = self._workspace.content

    def get_scan_paths(self) -> List[Path]:
        """Get effective scan paths based on configuration"""
        paths = set()
        paths.update(p.path for p in self._scan_paths)
        return sorted(paths)

    def get_recursive_paths(self) -> Set[Path]:
        """Get paths that should be scanned recursively"""
        return {p.path for p in self._scan_paths if p.is_recursive}

    def is_path_recursive(self, path: Path) -> bool:
        """Check if a path is configured for recursive scanning"""
        return any(scan_path.is_recursive and scan_path.path == path 
                  for scan_path in self._scan_paths)

    @property
    def paths(self) -> Set[Path]:
        return {p.path for p in self._scan_paths}

    @property
    def recursive_paths(self) -> Set[Path]:
        return self.get_recursive_paths()

    def clear(self) -> None:
        """Clear workspace settings while maintaining current directory in scan paths"""
        self._content = WorksetContent()

    def setup_preview_dir(self) -> Path:
        """Creates and sets up a preview directory with current workspace contents.
        
        Returns:
            Path: The path to the preview directory
        """
        return setup_preview_directory()

    def show(self) -> None:
        """Display analysis of current workset content."""
        show_workset_analysis(
            files=self._content.files,
            scan_paths=self._scan_paths,
            cache_blocks=self.get_cache_blocks()
        )

    def get_cache_blocks(self) -> Tuple[List[FileInfo], List[FileInfo], List[FileInfo], List[FileInfo]]:
        """Get files grouped into time-based cache blocks.
        
        Returns:
            Tuple of 4 lists containing FileInfo objects:
            - Last 5 minutes
            - Last hour
            - Last 24 hours
            - Older files
        """
        time_ranges = [300, 3600, 86400]  # 5min, 1h, 24h
        blocks: List[List[FileInfo]] = [[] for _ in range(4)]
        
        for file_info in sorted(self._content.files, key=lambda f: f.seconds_ago):
            # Will return 3 if file is older than all thresholds
            block_idx = next((i for i, threshold in enumerate(time_ranges) 
                            if file_info.seconds_ago <= threshold), 3)
            blocks[block_idx].append(file_info)
            
        return tuple(blocks)

    def setup_preview_directory(self) -> Path:
        """Create a temporary directory with a copy of the workspace contents.
        
        Creates a named temporary directory and copies the current workspace
        contents into it for preview purposes. Respects .gitignore patterns
        and excludes .git directory.
        
        Returns:
            Path: The path to the temporary preview directory
        """
        # Create a named temporary directory
        preview_dir = Path(tempfile.mkdtemp(prefix='janito_preview_'))
        
        try:
            # Read .gitignore if it exists
            gitignore_path = config.workspace_dir / '.gitignore'
            if gitignore_path.exists():
                gitignore = gitignore_path.read_text().splitlines()
                # Always ignore .git directory
                gitignore.append('.git')
                spec = pathspec.PathSpec.from_lines('gitwildmatch', gitignore)
            else:
                # If no .gitignore exists, only ignore .git
                spec = pathspec.PathSpec.from_lines('gitwildmatch', ['.git'])

            # Copy workspace contents to preview directory
            for item in config.workspace_dir.iterdir():
                # Get relative path for gitignore matching
                rel_path = item.relative_to(config.workspace_dir)
                
                # Skip if matches gitignore patterns
                if spec.match_file(str(rel_path)):
                    continue
                
                # Skip hidden files/directories except .gitignore
                if item.name.startswith('.') and item.name != '.gitignore':
                    continue
                    
                if item.is_dir():
                    # For directories, we need to filter contents based on gitignore
                    def copy_filtered(src, dst):
                        shutil.copytree(
                            src, 
                            dst,
                            ignore=lambda d, files: [
                                f for f in files 
                                if spec.match_file(str(Path(d).relative_to(config.workspace_dir) / f))
                            ]
                        )
                    
                    copy_filtered(item, preview_dir / item.name)
                else:
                    shutil.copy2(item, preview_dir / item.name)
                    
            return preview_dir
            
        except Exception as e:
            # Clean up the temporary directory if something goes wrong
            shutil.rmtree(preview_dir, ignore_errors=True)
            raise RuntimeError(f"Failed to setup preview directory: {e}")

