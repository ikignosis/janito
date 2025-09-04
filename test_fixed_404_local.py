#!/usr/bin/env python3
"""Test script to verify fixed 404 error reporting with local mock"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'janito'))

from unittest.mock import Mock, patch
import requests
from janito.plugins.tools.fetch_url import FetchUrl

def test_fixed_404_local():
    """Test with mocked 404 response"""
    
    # Create a mock response with 404 status
    mock_response = Mock()
    mock_response.status_code = 404
    
    # Create a mock HTTPError
    mock_error = requests.exceptions.HTTPError("404 Client Error")
    mock_error.response = mock_response
    
    tool = FetchUrl()
    
    with patch.object(tool.session, 'get', side_effect=mock_error):
        result = tool.run(url="https://example.com/test")
        print(f"Result: {result}")
        
        if "Not Found" in result:
            print("✅ SUCCESS: 404 is correctly reported as 'Not Found'")
        elif "Client Error" in result:
            print("❌ ISSUE: 404 is still falling back to generic 'Client Error'")
        else:
            print(f"❓ UNEXPECTED: {result}")

if __name__ == "__main__":
    test_fixed_404_local()