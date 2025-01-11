import tempfile
import os
from modify_file import ModifyFile
from executor import Executor

def test_modify_file_with_target_dir():
    # Create a temporary directory structure
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a subdirectory structure
        src_dir = os.path.join(temp_dir, "src")
        os.makedirs(src_dir)
        
        # Create test file in the subdirectory
        test_file = "data_processor.py"
        file_path = os.path.join(src_dir, test_file)
        
        with open(file_path, 'w') as f:
            f.write("""class DataProcessor:
    def process(self):
        pass
""")

        # Create executor with ModifyFile class and global target_dir
        executor = Executor([ModifyFile], target_dir=src_dir)
        
        # Execute modification through executor
        executor.execute("""
        Modify File
        name: data_processor.py
        - Replace Block
          start_context:
.    def process(self):
          end_context:
.        pass
          new_content:
.    def process(self):
.        return "processed"
          preserve_context: false
        ===
        """)

        # Verify changes
        with open(file_path, 'r') as file:
            content = file.read()
            expected = """class DataProcessor:
    def process(self):
        return "processed"
"""
            # Normalize line endings and trailing whitespace
            content = '\n'.join(line.rstrip() for line in content.splitlines())
            expected = '\n'.join(line.rstrip() for line in expected.splitlines())
            assert content == expected, f"Expected:\n{expected}\nGot:\n{content}"

        print("Target directory test passed!")

if __name__ == "__main__":
    test_modify_file_with_target_dir() 