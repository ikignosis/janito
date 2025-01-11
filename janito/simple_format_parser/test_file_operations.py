import os
import tempfile
from executor import Executor
from file_operations import CreateFile, DeleteFile, RenameFile

def test_file_operations():
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a subdirectory structure
        src_dir = os.path.join(temp_dir, "src")
        config_dir = os.path.join(src_dir, "config")
        
        # Create executor with file operation classes and target directory
        executor = Executor(
            [CreateFile, DeleteFile, RenameFile],
            target_dir=src_dir
        )
        
        # Test creating a file in a subdirectory
        executor.execute("""
        Create File
        name: config/settings.json
        content:
.{
.    "version": "1.0",
.    "environment": "test"
.}
        ===
        """)
        
        # Verify file was created
        settings_path = os.path.join(config_dir, "settings.json")
        assert os.path.exists(settings_path), "Settings file was not created"
        with open(settings_path, 'r') as f:
            content = f.read().strip()
            # Normalize content by removing whitespace
            content = ''.join(content.split())
            expected = ''.join('{"version":"1.0","environment":"test"}'.split())
            assert content == expected, f"Expected: {expected}, Got: {content}"
        
        # Test renaming the file
        executor.execute("""
        Rename File
        name: config/settings.json
        new_name: config/settings.v1.json
        ===
        """)
        
        # Verify rename
        old_path = settings_path
        new_path = os.path.join(config_dir, "settings.v1.json")
        assert not os.path.exists(old_path), "Old file still exists"
        assert os.path.exists(new_path), "New file does not exist"
        
        # Test deleting the file
        executor.execute("""
        Delete File
        name: config/settings.v1.json
        ===
        """)
        
        # Verify deletion
        assert not os.path.exists(new_path), "File was not deleted"
        
        print("All file operations tests passed!")

if __name__ == "__main__":
    test_file_operations() 