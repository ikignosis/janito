#!/usr/bin/env python3
"""Test script to verify 404 error reporting with a real URL"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'janito'))

from janito.plugins.tools.fetch_url import FetchUrl

def test_real_404():
    """Test with a URL that should return 404"""
    tool = FetchUrl()
    
    # Use a URL that definitely doesn't exist
    result = tool.run(url="https://httpbin.org/status/404")
    print(f"Result: {result}")

if __name__ == "__main__":
    test_real_404()