from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Set, Tuple
from sys import maxsize
from janito.config import config
from enum import auto, Enum

@dataclass
class FileInfo:
    """Represents a file's basic information"""
    name: str  # Relative path from workspace root
    content: str
    seconds_ago: int = 0  # Seconds since last modification

class ScanType(Enum):
    """Type of path scanning"""
    PLAIN = auto()
    RECURSIVE = auto()

@dataclass
class ScanPath:
    """Represents a path to be scanned"""
    path: Path
    scan_type: ScanType = ScanType.PLAIN

    @property
    def is_recursive(self) -> bool:
        return self.scan_type == ScanType.RECURSIVE

@dataclass
class WorksetContent:
    """Represents workset content and statistics."""
    files: List[FileInfo] = field(default_factory=list)
    scanned_paths: Set[Path] = field(default_factory=set)
    dir_counts: Dict[str, int] = field(default_factory=dict)
    dir_sizes: Dict[str, int] = field(default_factory=dict)
    file_types: Dict[str, int] = field(default_factory=dict)
    scan_completed: bool = False
    analyzed: bool = False

    def clear(self) -> None:
        """Reset all content"""
        self.files = []
        self.scanned_paths = set()
        self.dir_counts = {}
        self.dir_sizes = {}
        self.file_types = {}
        self.scan_completed = False
        self.analyzed = False

    def add_file(self, file_info: FileInfo) -> None:
        """Add a file to the content and update statistics"""
        self.files.append(file_info)
        
        # Update file type stats
        suffix = Path(file_info.name).suffix.lower() or 'no_ext'
        self.file_types[suffix] = self.file_types.get(suffix, 0) + 1
        
        # Update directory stats
        dir_path = str(Path(file_info.name).parent)
        self.dir_counts[dir_path] = self.dir_counts.get(dir_path, 0) + 1
        self.dir_sizes[dir_path] = self.dir_sizes.get(dir_path, 0) + len(file_info.content.encode('utf-8'))

    def get_file_info(self, time_ranges: List[int] = None) -> Tuple[List[FileInfo], List[FileInfo], List[FileInfo], List[FileInfo]]:
        """Get file information grouped into 4 blocks based on modification time ranges."""
        if not time_ranges:
            time_ranges = [300, 3600, 86400, maxsize]  # 5min, 1h, 24h, rest
        else:
            time_ranges = [int(x) for x in time_ranges[:3]] + [maxsize]
            if len(time_ranges) < 4:
                time_ranges.extend([maxsize] * (4 - len(time_ranges)))
        time_ranges.sort()

        blocks = [[] for _ in range(4)]
        
        def get_range_index(seconds: int) -> int:
            for i, threshold in enumerate(time_ranges):
                if seconds <= threshold:
                    return i
            return len(time_ranges) - 1

        # Sort and group files by modification time
        sorted_files = sorted(self.files, key=lambda f: f.seconds_ago)
        for file_info in sorted_files:
            block_idx = get_range_index(file_info.seconds_ago)
            blocks[block_idx].append(file_info)

        return tuple(blocks)

    @property
    def content_size(self) -> int:
        """Get total content size in bytes"""
        return sum(len(f.content.encode('utf-8')) for f in self.files)

    @property
    def file_count(self) -> int:
        """Get total number of files"""
        return len(self.files)