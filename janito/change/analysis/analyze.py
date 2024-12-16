"""Core analysis functionality."""

from typing import Optional

from janito.agents import agent
from janito.common import progress_send_message
from janito.config import config
from .display import format_analysis
from .options import AnalysisOption, parse_analysis_options
from .prompts import (
    build_request_analysis_prompt,
    get_option_selection,
    validate_option_letter
)

def analyze_request(
    request: str,        
    files_content_xml: str,
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
    prompt = build_request_analysis_prompt(request, files_content_xml)
    response = progress_send_message(prompt)
    
    # Parse options
    options = parse_analysis_options(response)
    if not options:
        return None

    if pre_select:
        return options[pre_select.upper()]

    if config.tui:
        from janito.tui import TuiApp
        app = TuiApp(options=options)
        app.run()
        return app.selected_option
        
    # Display formatted analysis in terminal mode
    format_analysis(response, config.raw)
    
    # Get user selection
    while True:
        selection = get_option_selection()
        
        if selection == 'M':
            return None
            
        if validate_option_letter(selection, options):
            selected_option = options[selection.upper()]
            return selected_option