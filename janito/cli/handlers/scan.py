from pathlib import Path
from typing import List
from janito.workspace import preview_scan
from ..base import BaseCLIHandler

class ScanHandler(BaseCLIHandler):
    def handle(self, paths_to_scan: List[Path]):
        """Preview files that would be analyzed"""
        preview_scan(paths_to_scan)