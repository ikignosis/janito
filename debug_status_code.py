#!/usr/bin/env python3
"""Debug script to check actual status code handling"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'janito'))

import requests

def debug_status_code():
    """Debug the actual status code we get"""
    
    urls = [
        "https://httpbin.org/status/404",
        "https://httpstat.us/404",
        "https://example.com/nonexistent"
    ]
    
    for url in urls:
        print(f"\nTesting: {url}")
        try:
            session = requests.Session()
            response = session.get(url, timeout=10)
            print(f"  Status: {response.status_code}")
            print(f"  Reason: {response.reason}")
            response.raise_for_status()
        except requests.exceptions.HTTPError as http_err:
            print(f"  HTTPError: {http_err}")
            print(f"  http_err.response: {http_err.response}")
            print(f"  http_err.response.status_code: {http_err.response.status_code if http_err.response else 'None'}")
            print(f"  http_err.response.reason: {http_err.response.reason if http_err.response else 'None'}")
        except Exception as e:
            print(f"  Other error: {e}")

if __name__ == "__main__":
    debug_status_code()