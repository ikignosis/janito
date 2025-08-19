#!/usr/bin/env python3
"""
Test script to verify that loop protection only triggers when the method is called
with the same value for the watched kwarg.
"""

import time
from janito.tools.loop_protection_decorator import protect_against_loops


class TestTool:
    """Test tool to demonstrate key_field protection behavior."""

    def __init__(self):
        self.call_count = 0

    @protect_against_loops(max_calls=3, time_window=5.0, key_field="target_path")
    def process_file(self, target_path: str, operation: str = "read") -> str:
        """Process a file with loop protection based on target_path."""
        self.call_count += 1
        return f"Processing {target_path} with operation {operation} (call #{self.call_count})"


def test_key_field_protection():
    """Test that protection only triggers for same key_field value."""
    print("=== Testing Key Field Protection ===\n")

    tool = TestTool()

    print(
        "1. Testing with different target_path values (should NOT trigger protection):"
    )
    try:
        for i in range(5):
            result = tool.process_file(f"/path/file_{i}.txt")
            print(f"   {result}")
        print("   ✓ No protection triggered - different paths")
    except RuntimeError as e:
        print(f"   ✗ Unexpected protection triggered: {e}")

    print("\n2. Testing with same target_path value (SHOULD trigger protection):")
    try:
        for i in range(4):  # 4 calls > 3 limit
            result = tool.process_file("/path/same_file.txt")
            print(f"   {result}")
        print("   ✗ Protection should have triggered but didn't")
    except RuntimeError as e:
        print(f"   ✓ Expected protection triggered: {e}")

    print("\n3. Testing with same path but different parameter order:")
    tool2 = TestTool()
    try:
        # Test positional argument
        for i in range(4):
            result = tool2.process_file("/path/positional_file.txt", "write")
            print(f"   {result}")
        print("   ✗ Protection should have triggered but didn't")
    except RuntimeError as e:
        print(f"   ✓ Expected protection triggered: {e}")

    print("\n4. Testing mixed scenarios:")
    tool3 = TestTool()
    try:
        # Mix of different and same paths
        paths = [
            "file1.txt",
            "file2.txt",
            "file1.txt",
            "file3.txt",
            "file1.txt",
            "file1.txt",
        ]
        for path in paths:
            result = tool3.process_file(path)
            print(f"   Processing {path}: {result}")
        print("   ✗ Protection should have triggered for file1.txt")
    except RuntimeError as e:
        print(f"   ✓ Expected protection triggered: {e}")


def test_without_key_field():
    """Test that without key_field, protection is based on function name."""
    print("\n=== Testing Without Key Field ===\n")

    class TestTool2:
        @protect_against_loops(max_calls=2, time_window=5.0)
        def generic_operation(self, path: str) -> str:
            return f"Processing {path}"

    tool = TestTool2()

    try:
        # All calls should count towards the same limit regardless of path
        for i in range(3):
            result = tool.generic_operation(f"/path/file_{i}.txt")
            print(f"   {result}")
        print("   ✗ Protection should have triggered")
    except RuntimeError as e:
        print(f"   ✓ Expected protection triggered: {e}")


if __name__ == "__main__":
    test_key_field_protection()
    test_without_key_field()
