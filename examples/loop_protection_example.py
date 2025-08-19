#!/usr/bin/env python3
"""
Example demonstrating the loop protection decorator.

This example shows how to use the @protect_against_loops decorator
to prevent excessive file operations in tools.
"""

from janito.tools.loop_protection_decorator import protect_against_loops
from janito.tools.loop_protection import LoopProtection


class ExampleFileReader:
    """Example tool that reads files with loop protection."""

    def __init__(self):
        self.last_result = None

    @protect_against_loops(max_calls=5, time_window=10.0)
    def read_file(self, path: str) -> str:
        """Read a single file with loop protection.

        Args:
            path (str): Path to the file to read

        Returns:
            str: Content of the file
        """
        print(f"Reading file: {path}")
        # Simulate reading a file
        return f"Content of {path}"

    @protect_against_loops(max_calls=5, time_window=10.0)
    def read_multiple_files(self, file_paths: list) -> dict:
        """Read multiple files with loop protection.

        Args:
            file_paths (list): List of file paths to read

        Returns:
            dict: Mapping of file paths to their contents
        """
        results = {}
        for path in file_paths:
            print(f"Reading file: {path}")
            # Simulate reading a file
            results[path] = f"Content of {path}"
        return results


def demonstrate_loop_protection():
    """Demonstrate the loop protection functionality."""
    print("=== Loop Protection Example ===\n")

    # Create an instance of our example tool
    reader = ExampleFileReader()

    # Reset any existing tracking
    LoopProtection.instance().reset_tracking()

    print("1. Normal operation (within limits):")
    try:
        # These should work fine
        for i in range(3):
            result = reader.read_file("example.txt")
            print(f"   Attempt {i+1}: {result}")
    except RuntimeError as e:
        print(f"   Error: {e}")

    print("\n2. Exceeding the limit (5 operations in 10 seconds):")
    try:
        # This should trigger the loop protection
        for i in range(6):
            result = reader.read_file("example.txt")
            print(f"   Attempt {i+1}: {result}")
    except RuntimeError as e:
        print(f"   Error: {e}")

    print("\n3. Multiple files with loop protection:")
    try:
        # This should work fine for different files
        file_list = [f"file_{i}.txt" for i in range(3)]
        results = reader.read_multiple_files(file_list)
        for path, content in results.items():
            print(f"   {path}: {content}")
    except RuntimeError as e:
        print(f"   Error: {e}")

    print("\n4. Multiple files exceeding limit:")
    try:
        # This should trigger loop protection
        file_list = ["same_file.txt"] * 6
        results = reader.read_multiple_files(file_list)
        for path, content in results.items():
            print(f"   {path}: {content}")
    except RuntimeError as e:
        print(f"   Error: {e}")


if __name__ == "__main__":
    demonstrate_loop_protection()
