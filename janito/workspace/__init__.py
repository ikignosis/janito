from .manager import WorkspaceManager
from .scan import preview_scan, collect_files_content, is_dir_empty

# Create singleton instance
workspace = WorkspaceManager.get_instance()

__all__ = ['workspace', 'preview_scan', 'collect_files_content', 'is_dir_empty']