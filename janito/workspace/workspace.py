from pathlib import Path
from typing import List, Set, Tuple
import time
from rich.console import Console
from janito.config import config
from .types import WorksetContent
from .workset import Workset

class Workspace:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init()
        return cls._instance

    def _init(self):
        self._content = WorksetContent()
        self._workset = Workset()
        self._workset._workspace = self

    @property
    def content(self) -> str:
        return self._content.content

    @content.setter
    def content(self, value: str):
        self._content.content = value

    @property
    def scan_completed(self) -> bool:
        return self._content.scan_completed

    @scan_completed.setter
    def scan_completed(self, value: bool):
        self._content.scan_completed = value

    @property
    def _analyzed(self) -> bool:
        return self._content.analyzed

    @_analyzed.setter
    def _analyzed(self, value: bool):
        self._content.analyzed = value

    def _scan_paths(self, paths: List[Path]) -> Tuple[List[str], List[str], List[str], List[str]]:
        """Internal scanning method used by Workset"""
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
                    if self._workset.is_path_recursive(path):
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
                # Added .toml to supported extensions
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

    def clear(self) -> None:
        self.content = ""
        self.scan_completed = False
        self._analyzed = False
