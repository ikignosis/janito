from pathlib import Path
from typing import List
from janito.workspace import workspace
from ..base import BaseCLIHandler

class ScanHandler(BaseCLIHandler):
    def handle(self, paths_to_scan: List[Path]):
        """Preview files that would be analyzed"""
        workspace.refresh(paths_to_scan)
        workspace.analyze()