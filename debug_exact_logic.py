#!/usr/bin/env python3
"""Debug script to trace the exact logic"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'janito'))

import requests

def debug_exact_logic():
    """Debug the exact logic in fetch_url"""
    
    url = "https://httpbin.org/status/404"
    
    try:
        session = requests.Session()
        response = session.get(url, timeout=10)
        response.raise_for_status()
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTPError: {http_err}")
        
        # Test the exact line from fetch_url
        status_code = http_err.response.status_code if http_err.response else None
        print(f"status_code = {status_code}")
        
        # Test the condition
        print(f"400 <= status_code < 500: {400 <= status_code < 500 if status_code else False}")
        
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
        
        description = status_descriptions.get(status_code, "Client Error")
        print(f"description = {description}")
        
        # Test the final message
        error_message = f"HTTP {status_code} {description}"
        print(f"error_message = {error_message}")

if __name__ == "__main__":
    debug_exact_logic()