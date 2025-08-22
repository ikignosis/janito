#!/usr/bin/env python3
"""
Test file to check HTTP error handling in janito's fetch_url functionality.
This test will attempt to fetch URLs that should return various HTTP errors.
"""

import pytest
import sys
import os

# Add the janito package to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "."))

from janito.tools.adapters.local.fetch_url import FetchUrlTool


class TestHttpErrors:
    """Test HTTP error handling in fetch_url functionality."""

    def test_404_error(self):
        """Test handling of 404 Not Found errors."""
        fetcher = FetchUrlTool()

        # Use a URL that should return 404
        result = fetcher.run("https://httpstat.us/404")

        # Should contain error information
        assert "HTTP Error" in result or "404" in result or "Not Found" in result
        print(f"404 test result: {result}")

    def test_403_error(self):
        """Test handling of 403 Forbidden errors."""
        fetcher = FetchUrlTool()

        # Use a URL that should return 403
        result = fetcher.run("https://httpstat.us/403")

        # Should contain error information
        assert "HTTP Error" in result or "403" in result or "Forbidden" in result
        print(f"403 test result: {result}")

    def test_500_error(self):
        """Test handling of 500 Internal Server Error."""
        fetcher = FetchUrlTool()

        # Use a URL that should return 500
        result = fetcher.run("https://httpstat.us/500")

        # Should contain error information
        assert "HTTP Error" in result or "500" in result or "Server Error" in result
        print(f"500 test result: {result}")

    def test_timeout_error(self):
        """Test handling of timeout errors."""
        fetcher = FetchUrlTool()

        # Use a URL that delays response and set short timeout
        result = fetcher.run("https://httpstat.us/200?sleep=5000", timeout=1)

        # Should contain timeout or error information
        assert "timeout" in result.lower() or "error" in result.lower()
        print(f"Timeout test result: {result}")

    def test_invalid_url_error(self):
        """Test handling of invalid URLs."""
        fetcher = FetchUrlTool()

        # Use an invalid URL
        result = fetcher.run("https://this-domain-does-not-exist-12345.com")

        # Should contain error information
        assert "error" in result.lower() or "failed" in result.lower()
        print(f"Invalid URL test result: {result}")

    def test_blocked_url(self):
        """Test handling of blocked URLs (whitelist functionality)."""
        fetcher = FetchUrlTool()

        # Try to fetch a URL that might be blocked
        # Note: This depends on the current whitelist configuration
        result = fetcher.run("http://malware-testing.com")

        # Should contain blocked information or proceed normally
        print(f"Blocked URL test result: {result}")

    def test_successful_request(self):
        """Test that successful requests still work."""
        fetcher = FetchUrlTool()

        # Use a URL that should return 200
        result = fetcher.run("https://httpstat.us/200")

        # Should contain the expected content
        assert "200" in result or "OK" in result
        print(f"Successful request test result: {result[:100]}...")


if __name__ == "__main__":
    # Run tests when executed directly
    pytest.main([__file__, "-v", "-s"])
