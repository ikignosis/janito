#!/usr/bin/env python3
"""Debug script to trace fetch_url behavior with detailed logging"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'janito'))

import requests
from janito.plugins.tools.fetch_url import FetchUrl

def debug_detailed():
    """Debug the fetch_url behavior with detailed logging"""
    
    url = "https://httpbin.org/status/404"
    
    # Let's manually trace the code flow
    print("Testing URL:", url)
    
    try:
        session = requests.Session()
        response = session.get(url, timeout=10)
        print(f"Response status: {response.status_code}")
        response.raise_for_status()
    except requests.exceptions.HTTPError as http_err:
        status_code = http_err.response.status_code if http_err.response else None
        print(f"Caught HTTPError with status: {status_code}")
        
        # Simulate the exact code from fetch_url
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
        
        if status_code and 400 <= status_code < 500:
            description = status_descriptions.get(status_code, "Client Error")
            error_message = f"HTTP {status_code} {description}"
            print(f"Should return: {error_message}")
        elif status_code and 500 <= status_code < 600:
            description = status_descriptions.get(status_code, "Server Error")
            error_message = f"HTTP {status_code} {description}"
            print(f"Should return: {error_message}")
        else:
            status_code_str = str(status_code) if status_code else "Error"
            description = status_descriptions.get(
                status_code,
                (
                    "Server Error"
                    if status_code and status_code >= 500
                    else "Client Error"
                ),
            )
            error_message = f"HTTP {status_code_str} {description}"
            print(f"Should return: {error_message}")
    
    # Now test the actual tool
    tool = FetchUrl()
    result = tool.run(url=url)
    print(f"Actual tool result: {result}")

if __name__ == "__main__":
    debug_detailed()