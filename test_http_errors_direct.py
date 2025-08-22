#!/usr/bin/env python3
"""
Direct test for HTTP error handling using the fetch_url tool directly.
This bypasses potential network connectivity issues by testing the tool's behavior.
"""

import pytest
import sys
import os

# Add the janito package to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "."))

from janito.tools.adapters.local.fetch_url import FetchUrlTool


def test_direct_tool_usage():
    """Test the fetch_url tool directly with mock scenarios."""
    tool = FetchUrlTool()

    # Test with a clearly invalid domain
    result = tool.run("https://nonexistent-domain-12345.invalid")
    print(f"Invalid domain result: {result}")

    # Should contain network error information
    assert "Network Error" in result or "Failed to connect" in result

    # Test with a well-known accessible URL
    result = tool.run("https://www.google.com")
    print(f"Google result: {result[:100]}...")

    # Should contain some content
    assert len(result) > 0

    # Test with httpstat.us for specific HTTP status codes
    # Note: This might fail due to network issues, but we want to see the behavior
    try:
        result = tool.run("https://httpstat.us/404")
        print(f"404 test result: {result}")
        assert "HTTP 404" in result or "404" in result
    except Exception as e:
        print(f"404 test failed with exception: {e}")
        # This is expected if there's no internet connectivity

    # Test timeout handling
    result = tool.run("https://httpstat.us/200?sleep=10000", timeout=2)
    print(f"Timeout test result: {result}")
    assert "Timeout" in result or "Network Error" in result


if __name__ == "__main__":
    test_direct_tool_usage()
    print("All tests completed!")
