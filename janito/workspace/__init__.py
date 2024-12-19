from .workset import Workset
from .scan import preview_scan, is_dir_empty

# Create singleton instance
workset = Workset()

__all__ = ['workset', 'preview_scan', 'is_dir_empty']