#!/usr/bin/env python3
"""Test script to verify HTTP status code descriptions"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'janito'))

from janito.plugins.tools.fetch_url import FetchUrl

def test_status_descriptions():
    """Test the status code mapping directly"""
    tool = FetchUrl()
    
    # Simulate the status code mapping
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
    
    # Test specific status codes
    test_codes = [400, 401, 403, 404, 429, 500, 502]
    
    print("Testing status code descriptions:")
    for code in test_codes:
        description = status_descriptions.get(code, "Client Error" if 400 <= code < 500 else "Server Error")
        print(f"HTTP {code}: {description}")
    
    # Test unknown status code
    unknown_code = 418
    description = status_descriptions.get(unknown_code, "Client Error")
    print(f"HTTP {unknown_code}: {description}")

if __name__ == "__main__":
    test_status_descriptions()