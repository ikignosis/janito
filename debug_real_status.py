#!/usr/bin/env python3
"""Debug script to check actual status code handling"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'janito'))

import requests

def debug_real_status():
    """Debug the actual status code we get"""
    
    url = "https://httpbin.org/status/404"
    
    try:
        session = requests.Session()
        response = session.get(url, timeout=10)
        print(f"Response status: {response.status_code}")
        print(f"Response reason: {response.reason}")
        response.raise_for_status()
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTPError: {http_err}")
        print(f"Type of http_err.response: {type(http_err.response)}")
        print(f"http_err.response.status_code: {http_err.response.status_code}")
        print(f"http_err.response.reason: {http_err.response.reason}")
        
        # Test the exact logic from fetch_url
        status_code = http_err.response.status_code if http_err.response else None
        print(f"Extracted status_code: {status_code}")
        
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
        print(f"Description: {description}")
        print(f"Expected result: HTTP {status_code} {description}")

if __name__ == "__main__":
    debug_real_status()