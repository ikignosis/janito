"""
This module provides file operations to be used with our executor
"""
import os

class FileOperation:
    """Base class for file operations that handles target_dir"""
    def __init__(self, name: str, target_dir: str = None):
        self.name = name
        self.target_dir = target_dir

    def _get_full_path(self, filename: str) -> str:
        """Get the full path to a file, considering target_dir if set"""
        if self.target_dir:
            return os.path.join(self.target_dir, filename)
        return filename

class CreateFile(FileOperation):
    def __init__(self, name: str, content: str, target_dir: str = None):
        super().__init__(name, target_dir)
        self.content = content

    def execute(self):
        full_path = self._get_full_path(self.name)
        # Ensure the directory exists
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, 'w') as file:
            file.write(self.content)

class DeleteFile(FileOperation):
    def __init__(self, name: str, target_dir: str = None):
        super().__init__(name, target_dir)

    def execute(self):
        full_path = self._get_full_path(self.name)
        os.remove(full_path)

class RenameFile(FileOperation):
    def __init__(self, name: str, new_name: str, target_dir: str = None):
        super().__init__(name, target_dir)
        self.new_name = new_name

    def execute(self):
        old_path = self._get_full_path(self.name)
        new_path = self._get_full_path(self.new_name)
        # Ensure the target directory exists for the new name
        os.makedirs(os.path.dirname(new_path), exist_ok=True)
        os.rename(old_path, new_path)

