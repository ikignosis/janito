#!/usr/bin/env python3
"""Test script to verify tool adapter converts argument names to lowercase."""

import tempfile
import os
import subprocess
import sys
from pathlib import Path
import json


def test_tool_adapter_lowercase_conversion():
    """Test that tool adapter converts argument names to lowercase."""
    print("Testing tool adapter lowercase conversion...")

    # Create a simple test tool that logs its arguments
    test_tool_content = '''
from janito.plugins.tools.local.adapter import register_local_tool
from janito.tools.tool_base import ToolBase, ToolPermissions

class TestArgsTool(ToolBase):
    tool_name = "test_args_tool"
    description = "Test tool to verify argument case conversion"
    permissions = ToolPermissions(read=True, write=False, execute=False)
    
    def execute(self, test_path: str, test_mode: str = "default") -> str:
        """Test tool that returns its arguments."""
        return f"Received: test_path={test_path}, test_mode={test_mode}"

register_local_tool(TestArgsTool)
'''

    # Create a temporary Python file with the test tool
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(test_tool_content)
        test_tool_file = f.name

    try:
        # Test with mixed case arguments
        print("\n1. Testing mixed case argument names...")
        
        # Create a simple test script that uses the tool adapter directly
        test_script = f'''
import sys
import os
sys.path.insert(0, os.path.join(os.getcwd(), "janito"))

# Import the test tool to register it
exec(open("{test_tool_file}").read())

from janito.plugins.tools.local.adapter import LocalToolsAdapter
from janito.llm.message_parts import FunctionCallMessagePart
import json

# Create a mock function object with mixed case arguments
class MockFunction:
    def __init__(self, name, arguments):
        self.name = name
        self.arguments = arguments

# Create adapter
adapter = LocalToolsAdapter()

# Test with mixed case arguments
mixed_case_args = {{"Test_Path": "/tmp/test", "Test_Mode": "verify"}}
function = MockFunction("test_args_tool", json.dumps(mixed_case_args))
message_part = FunctionCallMessagePart(tool_call_id="test_123", function=function)

# Execute and print result
result = adapter.execute_function_call_message_part(message_part)
print(f"Result: {{result}}")
'''

        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(test_script)
            test_script_file = f.name

        try:
            # Run the test script
            result = subprocess.run(
                [sys.executable, test_script_file],
                capture_output=True,
                text=True,
                cwd="/home/janito/janito"
            )

            print(f"Script output: {result.stdout}")
            print(f"Script stderr: {result.stderr}")
            
            # Check if the tool was executed successfully
            if result.returncode == 0 and "Received: test_path=/tmp/test, test_mode=verify" in result.stdout:
                print("✓ Mixed case arguments were successfully converted to lowercase")
                return True
            else:
                print("✗ Tool execution failed or arguments were not converted properly")
                return False

        finally:
            os.unlink(test_script_file)

    finally:
        os.unlink(test_tool_file)


if __name__ == "__main__":
    success = test_tool_adapter_lowercase_conversion()
    if success:
        print("\n🎉 Test passed!")
        sys.exit(0)
    else:
        print("\n❌ Test failed!")
        sys.exit(1)