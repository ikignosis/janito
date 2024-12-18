"""Analysis module for Janito.

This module provides functionality for analyzing and displaying code changes.
"""

from .options import AnalysisOption, parse_analysis_options
from .view import format_analysis, prompt_user, get_option_selection
from .prompts import (
    build_request_analysis_prompt,
    validate_option_letter
)
from .analyze import analyze_request

__all__ = [
    'AnalysisOption',
    'parse_analysis_options',
    'format_analysis',
    'build_request_analysis_prompt',
    'get_option_selection',
    'prompt_user',
    'validate_option_letter',
    'analyze_request'
]