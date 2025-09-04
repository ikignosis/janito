#!/usr/bin/env python3
"""Test script to verify multiple status codes"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'janito'))

from unittest.mock import Mock, patch
import requests
from janito.plugins.tools.fetch_url import FetchUrl

def test_multiple_status_codes():
    """Test with various status codes"""
    
    test_cases = [
        (400, "Bad Request"),
        (401, "Unauthorized"),
        (403, "Forbidden"),
        (404, "Not Found"),
        (429, "Too Many Requests"),
        (500, "Internal Server Error"),
        (503, "Service Unavailable"),
    ]
    
    tool = FetchUrl()
    
    for status_code, expected_description in test_cases:
        # Create a mock response
        mock_response = Mock()
        mock_response.status_code = status_code
        
        # Create a mock HTTPError
        mock_error = requests.exceptions.HTTPError(f"{status_code} Error")
        mock_error.response = mock_response
        
        with patch.object(tool.session, 'get', side_effect=mock_error):
            result = tool.run(url=f"https://example.com/test/{status_code}")
            print(f"Status {status_code}: {result}")
            
            if expected_description in result:
                print(f"  ✅ SUCCESS: {expected_description}")
            else:
                print(f"  ❌ ISSUE: Expected '{expected_description}' but got '{result}'")

if __name__ == "__main__":
    test_multiple_status_codes()