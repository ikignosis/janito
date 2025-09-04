#!/usr/bin/env python3
"""Test script to verify fixed 404 error reporting"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'janito'))

from janito.plugins.tools.fetch_url import FetchUrl

def test_fixed_404():
    """Test with a real 404 URL"""
    tool = FetchUrl()
    
    # Use a URL that should definitely return 404
    result = tool.run(url="https://example.com/nonexistent")
    print(f"Result: {result}")
    
    # Check if it contains "Not Found" or just "Client Error"
    if "Not Found" in result:
        print("✅ SUCCESS: 404 is correctly reported as 'Not Found'")
    elif "Client Error" in result:
        print("❌ ISSUE: 404 is still falling back to generic 'Client Error'")
    else:
        print(f"❓ UNEXPECTED: {result}")

if __name__ == "__main__":
    test_fixed_404()