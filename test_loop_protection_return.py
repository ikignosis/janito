#!/usr/bin/env python3
"""
Test script to verify that loop protection errors are returned as strings
instead of raising ToolCallException.
"""

import os
import tempfile
import time
from janito.tools.adapters.local.adapter import LocalToolsAdapter
from janito.tools.adapters.local.view_file import ViewFileTool


def test_loop_protection_returns_string():
    """Test that loop protection returns error message as string."""

    # Create a temporary file for testing
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("Test content\n" * 100)
        temp_file = f.name

    try:
        adapter = LocalToolsAdapter()
        adapter.register_tool(ViewFileTool)

        # First few calls should work
        for i in range(3):
            result = adapter.execute_tool("view_file", path=temp_file)
            assert isinstance(result, str)
            assert "Test content" in result
            print(f"Call {i+1}: Success")

        # Now trigger loop protection by making rapid calls
        print("\nTriggering loop protection...")

        # Make enough calls to trigger loop protection
        loop_protection_triggered = False
        for i in range(10):
            result = adapter.execute_tool("view_file", path=temp_file)
            print(f"Call {i+4}: {type(result).__name__}")

            # Check if we got a loop protection message
            if isinstance(result, str) and "Loop protection:" in result:
                print(f"✅ Loop protection triggered: {result}")
                loop_protection_triggered = True
                break

        assert loop_protection_triggered, "Loop protection should have been triggered"
        assert isinstance(
            result, str
        ), "Loop protection should return string, not raise exception"
        assert "Loop protection:" in result, "Should contain loop protection message"

        print(
            "✅ Test passed: Loop protection returns string instead of raising exception"
        )
        return True

    finally:
        # Clean up
        if os.path.exists(temp_file):
            os.unlink(temp_file)


if __name__ == "__main__":
    success = test_loop_protection_returns_string()
    exit(0 if success else 1)
