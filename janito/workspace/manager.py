from pathlib import Path
from typing import Dict, List, Optional, Set
from collections import defaultdict

class WorkspaceManager:
    _instance = None

    def __init__(self):
        self.content: Dict[Path, str] = {}
        self.file_stats: Dict[str, int] = defaultdict(int)
        self.dir_stats: Dict[Path, int] = defaultdict(int)
        self._analyzed = False

    @classmethod
    def get_instance(cls) -> "WorkspaceManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def collect_content(self, paths: List[Path]) -> None:
        """Collect and store content from specified paths"""
        from .scan import _scan_paths
        content_parts, _, _, _ = _scan_paths(paths)
        self.content = "\n".join(content_parts)
        self._analyzed = False

    def analyze(self) -> None:
        """Analyze workspace content and update statistics"""
        from .analysis import analyze_workspace_content
        if not self._analyzed and self.content:
            analyze_workspace_content(self.content)
            self._analyzed = True

    def get_content(self) -> str:
        """Get collected workspace content"""
        return self.content

    def clear(self) -> None:
        """Clear workspace content and stats"""
        self.content = {}
        self.file_stats.clear()
        self.dir_stats.clear()
        self._analyzed = False