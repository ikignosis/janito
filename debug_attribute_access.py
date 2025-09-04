#!/usr/bin/env python3
"""Debug script to check attribute access"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'janito'))

import requests

def debug_attribute_access():
    """Debug the attribute access issue"""
    
    url = "https://httpbin.org/status/404"
    
    try:
        session = requests.Session()
        response = session.get(url, timeout=10)
        response.raise_for_status()
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTPError: {http_err}")
        print(f"http_err.response: {http_err.response}")
        print(f"hasattr(http_err, 'response'): {hasattr(http_err, 'response')}")
        print(f"http_err.response is None: {http_err.response is None}")
        
        if http_err.response:
            print(f"http_err.response.status_code: {http_err.response.status_code}")
            print(f"hasattr(http_err.response, 'status_code'): {hasattr(http_err.response, 'status_code')}")
            
            # Test the exact logic
            status_code = http_err.response.status_code if http_err.response else None
            print(f"status_code: {status_code}")
            
            # Test alternative access
            try:
                status_code_alt = http_err.response.status_code
                print(f"status_code_alt: {status_code_alt}")
            except Exception as e:
                print(f"Error accessing status_code: {e}")

if __name__ == "__main__":
    debug_attribute_access()