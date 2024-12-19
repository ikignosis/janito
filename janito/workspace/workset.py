from pathlib import Path
from typing import List, Set, Tuple
import time
from rich.console import Console
from janito.config import config
from .types import WorksetContent

class Workset:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init()
        return cls._instance

    def _init(self):
        self._include_paths: Set[Path] = set()
        self._recursive_paths: Set[Path] = set()
        self._skip_workspace: bool = False
        self._content = WorksetContent()

    def include(self, paths: List[Path]) -> None:
        self._include_paths = set(paths) if paths else set()

    def recursive(self, paths: List[Path]) -> None:
        self._recursive_paths = set(paths) if paths else set()

    def skip_workspace(self, skip: bool) -> None:
        self._skip_workspace = skip

    def refresh(self, paths: List[Path] = None) -> None:
        """Refresh content based on workset paths"""
        scan_paths = paths if paths is not None else self.get_scan_paths()
        content_parts, _, _, _ = self._scan_paths(scan_paths)
        self._content.content = "\n".join(content_parts)
        self._content.scan_completed = True
        self._content.analyzed = False
        self._content.scanned_paths = set(scan_paths)

    def _scan_paths(self, paths: List[Path]) -> Tuple[List[str], List[str], List[str], List[str]]:
        """Internal scanning method"""
        if config.debug:
            console = Console(stderr=True)
            console.print(f"\n[cyan]Debug: Starting scan of {len(paths)} paths[/cyan]")
            start_time = time.time()

        content_parts = []
        file_items = []
        skipped_files = []
        ignored_items = []
        processed_files: Set[Path] = set()

        for path in paths:
            if config.debug:
                console.print(f"[cyan]Debug: Processing path: {path}[/cyan]")
            self._scan_path(path, content_parts, file_items, skipped_files, 
                          ignored_items, processed_files)

        if config.debug:
            elapsed = time.time() - start_time
            console.print(f"[cyan]Debug: Scan completed in {elapsed:.2f}s[/cyan]")
            console.print(f"[cyan]Debug: Found {len(file_items)} files, "
                        f"Skipped {len(skipped_files)}, "
                        f"Ignored {len(ignored_items)}[/cyan]")

        return content_parts, file_items, skipped_files, ignored_items

    def _scan_path(self, path: Path, content_parts: List[str], file_items: List[str],
                   skipped_files: List[str], ignored_items: List[str], processed_files: Set[Path]) -> None:
        """Process a single path for scanning."""
        if path in processed_files:
            if config.debug:
                Console(stderr=True).print(f"[cyan]Debug: Already processed: {path}[/cyan]")
            return
            
        path = path.resolve()
        processed_files.add(path)

        if path.is_dir():
            try:
                if config.debug:
                    Console(stderr=True).print(f"[cyan]Debug: Scanning directory: {path}[/cyan]")
                for item in path.iterdir():
                    if item.name.startswith(('.', '__pycache__')):
                        if config.debug:
                            Console(stderr=True).print(f"[cyan]Debug: Skipping hidden/cache: {item}[/cyan]")
                        continue
                    if self.is_path_recursive(path):
                        self._scan_path(item, content_parts, file_items, skipped_files,
                                      ignored_items, processed_files)
                    elif item.is_file():
                        self._scan_path(item, content_parts, file_items, skipped_files,
                                      ignored_items, processed_files)
            except PermissionError:
                if config.debug:
                    Console(stderr=True).print(f"[red]Debug: Permission denied: {path}[/red]")
                ignored_items.append(str(path))
        elif path.is_file():
            try:
                if path.suffix.lower() in {'.py', '.md', '.txt', '.json', '.yaml', '.yml', '.toml'} or not path.suffix:
                    if config.debug:
                        Console(stderr=True).print(f"[cyan]Debug: Reading file: {path}[/cyan]")
                    content = path.read_text(encoding='utf-8')
                    content_parts.append(f"<file>\n<path>{path}</path>\n<content>\n{content}\n</content>\n</file>")
                    file_items.append(str(path))
                else:
                    if config.debug:
                        Console(stderr=True).print(f"[yellow]Debug: Unsupported file type: {path}[/yellow]")
                    skipped_files.append(str(path))
            except (UnicodeDecodeError, PermissionError) as e:
                if config.debug:
                    Console(stderr=True).print(f"[red]Debug: Error reading file {path}: {str(e)}[/red]")
                skipped_files.append(str(path))

    def analyze(self) -> None:
        """Analyze and display the workset content."""
        if not self._content.scan_completed:
            return
        if not self._content.analyzed and self._content.content:
            self.show()
            self._content.analyzed = True

    def get_scan_paths(self) -> List[Path]:
        """Get effective scan paths based on configuration"""
        paths = list(self._include_paths)
        if not self._skip_workspace:
            paths.insert(0, config.workspace_dir)
        return paths if paths else [config.workspace_dir]

    def is_path_recursive(self, path: Path) -> bool:
        return path in self._recursive_paths

    @property
    def paths(self) -> Set[Path]:
        return self._include_paths

    @property
    def recursive_paths(self) -> Set[Path]:
        return self._recursive_paths

    def clear(self) -> None:
        self._include_paths.clear()
        self._recursive_paths.clear()
        self._skip_workspace = False
        self._content = WorksetContent()

    def show(self) -> None:
        """Display analysis of current workset content."""
        from .show import show_workset_analysis
        show_workset_analysis(self)

    def _collect_stats(self) -> tuple[dict, dict, dict, list]:
        """Collect statistics from workspace content."""
        dir_counts = defaultdict(lambda: [0, 0])  # [count, size]
        file_types = defaultdict(int)
        current_path = None
        current_content = []

        # Parse content and collect stats
        for line in self._content.content.split('\n'):
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

        # Calculate path stats
        paths_stats = []
        scan_paths = self.get_scan_paths()
        for path in sorted(set(scan_paths)):
            base_path = Path(path)
            total_files = sum(count for d, [count, _] in dir_counts.items()
                            if Path(d).is_relative_to(base_path))
            total_size = sum(size for d, [_, size] in dir_counts.items()
                            if Path(d).is_relative_to(base_path))
            path_str = str(path.relative_to(config.workspace_dir))
            is_recursive = path in self.recursive_paths
            paths_stats.append(
                f"{path_str}{'/*' if is_recursive else '/'} "
                f"[{total_files} file(s), {self._format_size(total_size)}]"
            )

        return (
            {k: (v[0], v[1]) for k, v in dir_counts.items()},
            {k: v[1] for k, v in dir_counts.items()},
            file_types,
            paths_stats
        )

    def _format_size(self, size_bytes: int) -> str:
        """Format size in bytes to human readable format."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                break
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} {unit}"

    @property
    def content(self) -> str:
        return self._content.content

    @property
    def scan_completed(self) -> bool:
        return self._content.scan_completed

    @property
    def analyzed(self) -> bool:
        return self._content.analyzed