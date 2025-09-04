#!/usr/bin/env python3
"""Debug script to trace fetch_url behavior with mock response"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'janito'))

from unittest.mock import Mock, patch
import requests
from janito.plugins.tools.fetch_url import FetchUrl

def debug_with_mock():
    """Debug the fetch_url behavior with mocked response"""
    
    # Create a mock response with 404 status
    mock_response = Mock()
    mock_response.status_code = 404
    
    # Create a mock HTTPError
    mock_error = requests.exceptions.HTTPError("404 Client Error")
    mock_error.response = mock_response
    
    tool = FetchUrl()
    
    with patch.object(tool.session, 'get', side_effect=mock_error):
        result = tool.run(url="https://example.com/test")
        print(f"Tool result: {result}")
        
        # Let's also test the status code mapping directly
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
        
        description = status_descriptions.get(404, "Client Error")
        print(f"Expected: HTTP 404 {description}")

if __name__ == "__main__":
    debug_with_mock()