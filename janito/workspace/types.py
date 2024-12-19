from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Set

@dataclass
class WorksetContent:
    """Represents workset content and statistics."""
    content: str = ""
    scanned_paths: Set[Path] = None
    dir_counts: Dict[str, int] = None
    dir_sizes: Dict[str, int] = None
    file_types: Dict[str, int] = None
    file_paths: Set[Path] = None
    scan_completed: bool = False
    analyzed: bool = False

    def __post_init__(self):
        self.scanned_paths = set()
        self.dir_counts = {}
        self.dir_sizes = {}
        self.file_types = {}
        self.file_paths = set()

    @property
    def files(self) -> Set[Path]:
        """Get set of all scanned file paths."""
        if not self.file_paths and self.content:
            self.file_paths = {
                Path(line.replace('<path>', '').replace('</path>', '').strip())
                for line in self.content.split('\n')
                if line.startswith('<path>')
            }
        return self.file_paths
