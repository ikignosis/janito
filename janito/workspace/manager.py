from pathlib import Path
from typing import Dict, List, Optional, Set
from collections import defaultdict

class WorkspaceManager:
    """Manages workspace state and operations using singleton pattern."""
    _instance = None

    def __init__(self):
        if WorkspaceManager._instance is not None:
            raise RuntimeError("Use WorkspaceManager.get_instance() instead")
        self.content: str = ""
        self.scan_completed: bool = False
        self._analyzed: bool = False

    @classmethod
    def get_instance(cls) -> "WorkspaceManager":
        """Get singleton instance of WorkspaceManager."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def collect_content(self, paths: List[Path]) -> None:
        """Collect and store content from specified paths."""
        from .scan import _scan_paths
        content_parts, _, _, _ = _scan_paths(paths)
        self.content = "\n".join(content_parts)
        self.scan_completed = True
        self._analyzed = False

    def analyze(self) -> None:
        """Analyze workspace content and update statistics."""
        from .analysis import analyze_workspace_content
        if not self.scan_completed:
            return
        if not self._analyzed and self.content:
            analyze_workspace_content(self.content)
            self._analyzed = True

    def get_content(self) -> str:
        """Get collected workspace content."""
        return self.content

    def clear(self) -> None:
        """Clear workspace content and stats."""
        self.content = ""
        self.scan_completed = False
        self._analyzed = False