import os
import tempfile
from executor import Executor
from modify_file_content import ModifyFileContent

def test_modify_content():
    # Create a temporary test file
    with tempfile.TemporaryDirectory() as temp_dir:
        test_file = os.path.join(temp_dir, "test.txt")
        initial_content = """First line
def some_function():
    # BEGIN: validation
    value = 42
    result = value * 2
    print(f"Result: {result}")
    # END: validation
    return result
Last line
"""
        def reset_file():
            with open(test_file, 'w') as f:
                f.write(initial_content)

        # Test ReplaceBlock
        reset_file()
        executor = Executor([ModifyFileContent], target_dir=temp_dir)
        replace_statement = """
        Modify File Content
            name: test.txt
        - Replace Block
            before_lines:
            .    # BEGIN: validation
            after_lines:
            .    # END: validation
            new_content:
            .# BEGIN: new validation
            .new_value = 100
            .result = new_value + 50
            .print(f"New result: {result}")
            .# END: new validation
            new_indent: 4
        ===
        """
        executor.execute(replace_statement)
        with open(test_file, 'r') as f:
            content = f.read()
            assert 'new_value = 100' in content
            assert 'result = new_value + 50' in content
            assert 'def some_function():' in content
            assert 'print(f"New result: {result}")' in content
            assert 'return result' in content
            assert 'value = 42' not in content
            assert 'print(f"Result: {result}")' not in content
            assert content.count('# BEGIN: validation') == 0
            assert content.count('# END: validation') == 0
            assert content.count('# BEGIN: new validation') == 1
            assert content.count('# END: new validation') == 1

        # Test AdaptBlock
        reset_file()
        executor = Executor([ModifyFileContent], target_dir=temp_dir)
        adapt_statement = """
        Modify File Content
            name: test.txt
        - Adapt Block
            before_lines:
            .    # BEGIN: validation
            after_lines:
            .    # END: validation
            new_content:
            .modified_value = value + 10
            .result = modified_value * 3
            .print(f"Modified: {result}")
            new_indent: 4
        ===
        """
        executor.execute(adapt_statement)
        with open(test_file, 'r') as f:
            content = f.read()
            assert 'modified_value = value + 10' in content
            assert 'result = modified_value * 3' in content
            assert 'def some_function():' in content
            assert 'return result' in content
            assert 'value = 42' not in content
            assert content.count('# BEGIN: validation') == 1
            assert content.count('# END: validation') == 1

        # Test DeleteBlock
        reset_file()
        executor = Executor([ModifyFileContent], target_dir=temp_dir)
        delete_statement = """
        Modify File Content
            name: test.txt
        - Delete Block
            before_lines:
            .    value = 42
            after_lines:
            .    print(f"Result: {result}")
        ===
        """
        executor.execute(delete_statement)
        with open(test_file, 'r') as f:
            content = f.read()
            assert 'def some_function():' in content
            assert 'return result' in content
            assert 'value = 42' not in content
            assert 'result = value * 2' not in content
            assert 'print(f"Result: {result}")' not in content

        # Test AdaptBlock with only before_lines
        reset_file()
        executor = Executor([ModifyFileContent], target_dir=temp_dir)
        adapt_before_only_statement = """
        Modify File Content
            name: test.txt
        - Adapt Block
            before_lines:
            .    # BEGIN: validation
            new_content:
            .inserted_value = 200
            .print(f"Inserted: {inserted_value}")
            new_indent: 4
        ===
        """
        executor.execute(adapt_before_only_statement)
        with open(test_file, 'r') as f:
            content = f.readlines()
            prefix_idx = content.index('    # BEGIN: validation\n')
            assert content[prefix_idx + 1] == '    inserted_value = 200\n'
            assert content[prefix_idx + 2] == '    print(f"Inserted: {inserted_value}")\n'
            
            content_str = ''.join(content)
            assert 'value = 42' in content_str
            assert 'result = value * 2' in content_str
            assert '# END: validation' in content_str
            assert 'return result' in content_str
            assert 'def some_function():' in content_str
            assert content_str.count('# BEGIN: validation') == 1

        # Test DeleteBlock with only before_lines
        reset_file()
        executor = Executor([ModifyFileContent], target_dir=temp_dir)
        delete_before_only_statement = """
        Modify File Content
            name: test.txt
        - Delete Block
            before_lines:
            .    # BEGIN: validation
        ===
        """
        executor.execute(delete_before_only_statement)
        with open(test_file, 'r') as f:
            content = f.readlines()
            assert '    # BEGIN: validation\n' not in content
            assert '    value = 42\n' not in content
            assert '    result = value * 2\n' in content
            assert '    # END: validation\n' in content

        # Test DeleteBlock with only after_lines
        reset_file()
        executor = Executor([ModifyFileContent], target_dir=temp_dir)
        delete_after_only_statement = """
        Modify File Content
            name: test.txt
        - Delete Block
            after_lines:
            .    # END: validation
        ===
        """
        executor.execute(delete_after_only_statement)
        with open(test_file, 'r') as f:
            content = f.readlines()
            assert '    # BEGIN: validation\n' in content
            assert '    print(f"Result: {result}")\n' not in content
            assert '    # END: validation\n' not in content
            assert '    return result\n' in content

def test_multiline_contexts():
    # Create a temporary test file
    with tempfile.TemporaryDirectory() as temp_dir:
        test_file = os.path.join(temp_dir, "test.txt")
        initial_content = """First line
class Calculator:
    def compute_total(self, items):
        subtotal = 0
        tax_rate = 0.2
        for item in items:
            subtotal += item.price
        tax = subtotal * tax_rate
        total = subtotal + tax
        return total
Last line
"""
        def reset_file():
            with open(test_file, 'w') as f:
                f.write(initial_content)

        # Test ReplaceBlock
        reset_file()
        executor = Executor([ModifyFileContent], target_dir=temp_dir)
        modify_statement = """
        Modify File Content
            name: test.txt
        - Replace Block
            before_lines:
            .        subtotal = 0
            .        tax_rate = 0.2
            after_lines:
            .        total = subtotal + tax
            .        return total
            new_content:
            .base_total = sum(item.price for item in items)
            .tax = base_total * 0.15  # Updated tax rate
            new_indent: 8
        ===
        """
        executor.execute(modify_statement)

        # Verify replacement
        with open(test_file, 'r') as f:
            content = f.read()
            assert 'base_total = sum(item.price for item in items)' in content
            assert 'tax = base_total * 0.15' in content
            assert 'class Calculator:' in content
            assert 'def compute_total' in content
            assert 'subtotal = 0' not in content
            assert 'tax_rate = 0.2' not in content

        # Test DeleteBlock
        reset_file()
        executor = Executor([ModifyFileContent], target_dir=temp_dir)
        delete_statement = """
        Modify File Content
            name: test.txt
        - Delete Block
            before_lines:
            .        subtotal = 0
            .        tax_rate = 0.2
            after_lines:
            .        total = subtotal + tax
            .        return total
        ===
        """
        executor.execute(delete_statement)

        # Verify deletion
        with open(test_file, 'r') as f:
            content = f.read()
            assert 'class Calculator:' in content
            assert 'def compute_total' in content
            assert 'subtotal = 0' not in content
            assert 'tax_rate = 0.2' not in content
            assert 'for item in items:' not in content
            assert 'total = subtotal + tax' not in content

if __name__ == "__main__":
    test_modify_content()
    test_multiline_contexts()
    print("All tests passed!")