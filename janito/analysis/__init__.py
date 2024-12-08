"""Analysis module for Janito.

This module provides functionality for analyzing and displaying code changes.
"""

from .options import AnalysisOption, parse_analysis_options
from .display import (
    format_analysis,
    get_history_file_type,
    get_history_path,
    get_timestamp,
    save_to_file
)
from .prompts import (
    build_request_analysis_prompt,
    get_option_selection,
    prompt_user,
    validate_option_letter
)

__all__ = [
    'AnalysisOption',
    'parse_analysis_options',
    'format_analysis',
    'get_history_file_type',
    'get_history_path', 
    'get_timestamp',
    'save_to_file',
    'build_request_analysis_prompt',
    'get_option_selection',
    'prompt_user',
    'validate_option_letter'
]
