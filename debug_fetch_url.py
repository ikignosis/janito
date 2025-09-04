#!/usr/bin/env python3
"""Debug script to trace fetch_url behavior"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'janito'))

import requests
from janito.plugins.tools.fetch_url import FetchUrl

def debug_fetch_url():
    """Debug the fetch_url behavior step by step"""
    
    url = "https://httpbin.org/status/404"
    
    try:
        # Test direct requests behavior
        session = requests.Session()
        response = session.get(url, timeout=10)
        print(f"Direct request status: {response.status_code}")
        response.raise_for_status()
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTPError caught: {http_err}")
        print(f"Response status: {http_err.response.status_code if http_err.response else 'None'}")
        print(f"Response: {http_err.response}")
    
    # Test with our tool
    tool = FetchUrl()
    result = tool.run(url=url)
    print(f"Tool result: {result}")

if __name__ == "__main__":
    debug_fetch_url()