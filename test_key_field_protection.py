#!/usr/bin/env python3
"""
Test script to verify that key_field parameter works correctly in loop protection.
"""

import os
import tempfile
import time
from janito.tools.adapters.local.adapter import LocalToolsAdapter
from janito.tools.adapters.local.view_file import ViewFileTool


def test_key_field_protection():
    """Test that key_field parameter tracks calls per unique path."""

    # Create temporary files for testing
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f1:
        f1.write("File 1 content\n" * 10)
        temp_file1 = f1.name

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f2:
        f2.write("File 2 content\n" * 10)
        temp_file2 = f2.name

    try:
        adapter = LocalToolsAdapter()
        adapter.register_tool(ViewFileTool)

        print("Testing key_field protection...")

        # Test 1: Multiple calls to same file should trigger protection
        print("\n1. Testing same file protection:")
        for i in range(6):
            result = adapter.execute_tool("view_file", path=temp_file1)
            print(f"  File1 call {i+1}: {type(result).__name__}")
            if isinstance(result, str) and "Loop protection:" in result:
                print(f"  ✅ Protection triggered for file1: {result}")
                break
        else:
            print("  ❌ Protection not triggered for file1")
            return False

        # Test 2: Calls to different file should still work
        print("\n2. Testing different file still works:")
        result = adapter.execute_tool("view_file", path=temp_file2)
        if isinstance(result, str) and "File 2 content" in result:
            print("  ✅ Different file still accessible")
        else:
            print("  ❌ Different file blocked unexpectedly")
            return False

        # Test 3: After waiting, same file should work again
        print("\n3. Testing protection reset:")
        time.sleep(11)  # Wait longer than time_window
        result = adapter.execute_tool("view_file", path=temp_file1)
        if isinstance(result, str) and "File 1 content" in result:
            print("  ✅ Protection reset after time window")
        else:
            print("  ❌ Protection did not reset")
            return False

        print("\n✅ All key_field protection tests passed!")
        return True

    finally:
        # Clean up
        for temp_file in [temp_file1, temp_file2]:
            if os.path.exists(temp_file):
                os.unlink(temp_file)


if __name__ == "__main__":
    success = test_key_field_protection()
    exit(0 if success else 1)
