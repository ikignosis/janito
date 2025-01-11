import tempfile
import os
from modify_file import ModifyFile
from executor import Executor

def test_modify_indent():
    # Create a temporary test file with Python source code
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp:
        temp.write("""def process_data(records: list) -> dict:
    results = {}
    for record in records:
        if record.get('id'):
            # Simple validation and processing
            if record.get('value', 0) > 0:
                results[record['id']] = record['value']
    return results

def validate_record(record: dict) -> bool:
    # Basic validation
    if record.get('id'):
        return True
    return False""")
        temp_name = temp.name

    try:
        # Create executor with ModifyFile class
        executor = Executor([ModifyFile])
        
        # Execute modifications through executor
        executor.execute(f"""
        Modify File
        name: {temp_name}
        - Replace Block
          start_context:
.            if record.get('value', 0) > 0:
.                results[record['id']] = record['value']
          new_content:
.            if record.get('value', 0) > 0:
.                if record.get('status') == 'active':
.                    if record.get('name'):
.                        results[record['id']] = {{
.                            'value': record['value'],
.                            'name': record['name']
.                        }}
          indent: 12
          # preserve_context is false by default now
        - Replace Block
          start_context:
.    # Basic validation
.    if record.get('id'):
.        return True
.    return False
          new_content:
.    # Comprehensive validation
.    if not isinstance(record, dict):
.        return False
.    if not record.get('id'):
.        return False
.    if record.get('value', 0) < 0:
.        return False
.    if not record.get('name', '').strip():
.        return False
.    return True
          indent: 4
        ===
        """)

        # Verify changes
        with open(temp_name, 'r') as file:
            content = file.read()
            expected = """def process_data(records: list) -> dict:
    results = {}
    for record in records:
        if record.get('id'):
            # Simple validation and processing
            if record.get('value', 0) > 0:
                if record.get('status') == 'active':
                    if record.get('name'):
                        results[record['id']] = {
                            'value': record['value'],
                            'name': record['name']
                        }
    return results

def validate_record(record: dict) -> bool:
    # Comprehensive validation
    if not isinstance(record, dict):
        return False
    if not record.get('id'):
        return False
    if record.get('value', 0) < 0:
        return False
    if not record.get('name', '').strip():
        return False
    return True"""
            # Normalize line endings and trailing whitespace
            content = '\n'.join(line.rstrip() for line in content.splitlines())
            expected = '\n'.join(line.rstrip() for line in expected.splitlines())
            assert content == expected, f"Expected:\n{expected}\nGot:\n{content}"

        print("All modify_indent tests passed!")

    finally:
        # Clean up
        os.unlink(temp_name)


if __name__ == "__main__":
    test_modify_indent() 