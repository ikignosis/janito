#!/usr/bin/env python3
"""Test script to verify 404 error reporting"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'janito'))

from janito.plugins.tools.fetch_url import FetchUrl

def test_404():
    tool = FetchUrl()
    result = tool.run(url="https://httpstat.us/404")
    print(f"Result: {result}")

if __name__ == "__main__":
    test_404()