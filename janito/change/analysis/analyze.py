"""Core analysis functionality."""

from typing import Optional

from janito.agents import agent
from janito.common import progress_send_message
from janito.config import config
from .display import format_analysis, save_to_file
from .options import AnalysisOption, parse_analysis_options
from .prompts import (
    build_request_analysis_prompt,
    get_option_selection,
    validate_option_letter
)

def analyze_request(
    files_content: str,
    request: str,
    pre_select: str = ""
) -> Optional[AnalysisOption]:
    """
    Analyze changes and get user selection.
    
    Args:
        files_content: Content of files to analyze
        request: User's change request
        
    Returns:
        Selected AnalysisOption or None if modified
    """
    # Build and send prompt
    prompt = build_request_analysis_prompt(files_content, request)
    
 
    response = progress_send_message(prompt)
    
    # Save analysis response
    saved_path = save_to_file(response, "analysis")
    if config.verbose:
        print(f"Analysis saved to: {saved_path}")
    
    # Display formatted analysis
    format_analysis(response, config.raw)
    
    # Parse options
    options = parse_analysis_options(response)
    if not options:
        return None
    
    if pre_select:
        return options[pre_select.upper()]
        
    # Get user selection
    while True:

        selection = get_option_selection()
        
        if selection == 'M':
            return None
            
        if validate_option_letter(selection, options):
            selected_option = options[selection.upper()]
            saved_path = save_to_file(str(selected_option.__dict__), "selected")
            if config.verbose:
                print(f"Selected option saved to: {saved_path}")
            return selected_option
