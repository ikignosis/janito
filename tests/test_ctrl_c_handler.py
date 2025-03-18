"""
Test script for Ctrl+C handling during query execution.
"""
import sys
import signal
import threading
import time
from unittest.mock import patch, MagicMock

# Add parent directory to path to import janito modules
sys.path.append('.')

from janito.cli.agent import handle_query

def test_ctrl_c_handler():
    """
    Test that Ctrl+C during query execution prints token and tool usage.
    """
    # Mock the agent and other dependencies
    mock_agent = MagicMock()
    mock_agent.query.side_effect = KeyboardInterrupt()
    
    # Mock the generate_token_report function
    with patch('janito.cli.agent.initialize_agent', return_value=mock_agent), \
         patch('janito.cli.agent.generate_token_report') as mock_token_report, \
         patch('janito.tools.print_usage_stats') as mock_usage_stats, \
         patch('janito.cli.agent.sys.exit') as mock_exit:
        
        # Call handle_query, which should catch the KeyboardInterrupt
        handle_query("test query", 0.7, False, False)
        
        # Verify that token report and usage stats were called
        mock_token_report.assert_called_once()
        mock_usage_stats.assert_called_once()
        
        # Verify that sys.exit was called with code 130
        mock_exit.assert_called_once_with(130)
        
        print("✅ Test passed: Ctrl+C handler correctly prints token and tool usage")

if __name__ == "__main__":
    test_ctrl_c_handler()