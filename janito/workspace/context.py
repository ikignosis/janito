from typing import List, Dict, Optional
from pathlib import Path
from dataclasses import dataclass
from copy import deepcopy
from .models import ScanType
from janito.workspace.models import ScanPath
from . import workset

@dataclass
class WorksetState:
    """Stores workset state for restoration"""
    scan_paths: List[tuple[Path, ScanType]]

class WorksetContext:
    """Context manager for temporary workset modifications"""

    def __init__(self):
        self._previous_state: Optional[WorksetState] = None

    def _save_state(self) -> None:
        """Save current workset state"""
        self._previous_state = WorksetState(
            scan_paths=[(p.path, p.scan_type) for p in workset._scan_paths]
        )

    def _restore_state(self) -> None:
        """Restore previous workset state"""
        if self._previous_state:
            workset._scan_paths = [
                ScanPath(path=p, scan_type=t)
                for p, t in self._previous_state.scan_paths
            ]
            workset.refresh()

    def __enter__(self):
        """Save current state and return context"""
        self._save_state()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Restore previous state"""
        self._restore_state()
