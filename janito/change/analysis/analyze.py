"""Core analysis functionality."""

from typing import Optional
from janito.agents import agent
from janito.common import progress_send_message
from janito.config import config
from janito.workspace.workset import Workset
from .view import format_analysis
from .options import AnalysisOption, parse_analysis_options
from .prompts import (
    build_request_analysis_prompt,
    get_option_selection,
    validate_option_letter
)

def analyze_request(
    request: str,
    pre_select: str = "",
    single: bool = False
) -> Optional[AnalysisOption]:
    """
    Analyze changes and get user selection.
    
    Args:
        request: User's change request
        files_content_xml: Optional content of files to analyze
        pre_select: Optional pre-selected option letter
        
    Returns:
        Selected AnalysisOption or None if modified
    """
    if single:
        return None

    workset = Workset()  # Create workset instance
       
    # Build and send prompt using workset content directly
    prompt = build_request_analysis_prompt(request)
    response = progress_send_message(prompt)
    
    # Parse and handle options
    options = parse_analysis_options(response)
    if not options:
        return None

    if pre_select:
        return options.get(pre_select.upper())
        
    # Display formatted analysis in terminal mode
    format_analysis(response, config.raw)
    
    # Get user selection
    while True:
        selection = get_option_selection()
        
        if selection == 'M':
            return None
            
        if validate_option_letter(selection, options):
            return options[selection.upper()]