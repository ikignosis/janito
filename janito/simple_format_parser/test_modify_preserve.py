import tempfile
import os
from modify_file import ModifyFile
from executor import Executor

def test_modify_preserve_signature():
    # Create a temporary directory structure
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a subdirectory structure
        src_dir = os.path.join(temp_dir, "src")
        os.makedirs(src_dir)
        
        # Create test file in the subdirectory
        test_file = "calculator.py"
        file_path = os.path.join(src_dir, test_file)
        
        with open(file_path, 'w') as f:
            f.write("""class Calculator:
    def add(self, a, b):
        # Old implementation
        result = a + b
        return result
""")

        # Create executor with ModifyFile class and global target_dir
        executor = Executor([ModifyFile], target_dir=src_dir)
        
        # Execute modification through executor, preserving the function signature
        executor.execute("""
        Modify File
        name: calculator.py
        - Replace Block
          start_context:
.    def add(self, a, b):
          end_context:
.        return result
          new_content:
.        # New implementation
.        sum_result = a + b
.        return sum_result
          preserve_context: true
        ===
        """)

        # Verify changes
        with open(file_path, 'r') as file:
            content = file.read()
            expected = """class Calculator:
    def add(self, a, b):
        # New implementation
        sum_result = a + b
        return sum_result
"""
            # Normalize line endings and trailing whitespace
            content = '\n'.join(line.rstrip() for line in content.splitlines())
            expected = '\n'.join(line.rstrip() for line in expected.splitlines())
            assert content == expected, f"Expected:\n{expected}\nGot:\n{content}"

        print("Preserve context test passed!")

if __name__ == "__main__":
    test_modify_preserve_signature() 