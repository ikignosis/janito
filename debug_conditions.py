#!/usr/bin/env python3
"""Debug script to check the conditions"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'janito'))

import requests

def debug_conditions():
    """Debug the conditions in fetch_url"""
    
    # Simulate the exact scenario
    class MockResponse:
        def __init__(self, status_code):
            self.status_code = status_code
    
    class MockHTTPError:
        def __init__(self, status_code):
            self.response = MockResponse(status_code)
    
    # Test different status codes
    test_cases = [400, 401, 403, 404, 500, 503]
    
    for status_code in test_cases:
        print(f"\nTesting status code: {status_code}")
        
        mock_error = MockHTTPError(status_code)
        
        # Test the exact logic from fetch_url
        status_code_extracted = mock_error.response.status_code if mock_error.response else None
        print(f"  Extracted status_code: {status_code_extracted}")
        print(f"  Type: {type(status_code_extracted)}")
        
        # Test the conditions
        condition1 = status_code_extracted and 400 <= status_code_extracted < 500
        condition2 = status_code_extracted and 500 <= status_code_extracted < 600
        
        print(f"  400 <= status_code < 500: {condition1}")
        print(f"  500 <= status_code < 600: {condition2}")
        
        # Test the mapping
        status_descriptions = {
            400: "Bad Request",
            401: "Unauthorized",
            403: "Forbidden",
            404: "Not Found",
            405: "Method Not Allowed",
            408: "Request Timeout",
            409: "Conflict",
            410: "Gone",
            413: "Payload Too Large",
            414: "URI Too Long",
            415: "Unsupported Media Type",
            429: "Too Many Requests",
            500: "Internal Server Error",
            501: "Not Implemented",
            502: "Bad Gateway",
            503: "Service Unavailable",
            504: "Gateway Timeout",
            505: "HTTP Version Not Supported",
        }
        
        if condition1:
            description = status_descriptions.get(status_code_extracted, "Client Error")
            print(f"  Should return: HTTP {status_code_extracted} {description}")
        elif condition2:
            description = status_descriptions.get(status_code_extracted, "Server Error")
            print(f"  Should return: HTTP {status_code_extracted} {description}")
        else:
            status_code_str = str(status_code_extracted) if status_code_extracted else "Error"
            description = status_descriptions.get(
                status_code_extracted,
                (
                    "Server Error"
                    if status_code_extracted and status_code_extracted >= 500
                    else "Client Error"
                ),
            )
            print(f"  Should return: HTTP {status_code_str} {description}")

if __name__ == "__main__":
    debug_conditions()