"""
This module provides file operations to be used with our executor
"""
import os
from pathlib import Path

# Provide modify_file from it's own module considering it's complexity
from .modify_file import ModifyFile
from janito.simple_format_parser.executor import Executor

class FileOperation:
    """Base class for file operations that handles target_dir"""
    def __init__(self, name: Path, target_dir: Path = None):
        self.name = name
        self.target_dir = target_dir

    def _get_full_path(self, filename: Path) -> Path:
        """Get the full path to a file, considering target_dir if set"""
        if self.target_dir:
            return self.target_dir / filename
        return filename

class CreateFile(FileOperation):
    def __init__(self, name: Path, content: str, target_dir: Path = None):
        super().__init__(name, target_dir)
        self.content = content

    def execute(self):
        full_path = self._get_full_path(self.name)
        # Ensure the directory exists
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(self.content, encoding='utf-8')

class DeleteFile(FileOperation):
    def __init__(self, name: Path, target_dir: Path = None):
        super().__init__(name, target_dir)

    def execute(self):
        full_path = self._get_full_path(self.name)
        full_path.unlink()

class RenameFile(FileOperation):
    def __init__(self, name: Path, new_name: Path, target_dir: Path = None):
        super().__init__(name, target_dir)
        self.new_name = new_name

    def execute(self):
        old_path = self._get_full_path(self.name)
        new_path = self._get_full_path(self.new_name)
        # Ensure the target directory exists for the new name
        new_path.parent.mkdir(parents=True, exist_ok=True)
        old_path.rename(new_path)

class ReplaceFile(FileOperation):
    def __init__(self, name: Path, content: str, target_dir: Path = None):
        super().__init__(name, target_dir)
        self.content = content

    def execute(self):
        full_path = self._get_full_path(self.name)
        full_path.write_text(self.content, encoding='utf-8')

class FileOperationExecutor(Executor):
    def __init__(self, target_dir: Path):
        self.target_dir = target_dir
        super().__init__([CreateFile, DeleteFile, RenameFile, ReplaceFile, ModifyFile], target_dir=target_dir)
    
    def get_changes(self):
        """ Build a list of changes from the instances """
        changes = []
        for instance in self.instances:
            changes.append(instance)
        return changes


