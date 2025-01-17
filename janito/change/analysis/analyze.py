"""Core analysis functionality."""

from typing import Optional
from rich.console import Console
from janito.agents import agent
from janito.common import progress_send_message
from janito.config import config
from janito.workspace.workset import Workset
from .view import format_analysis
from .view.input import get_option_selection
from .options import AnalysisOption, parse_analysis_options
from .prompts import (
    build_request_analysis_prompt,
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
        Selected AnalysisOption or None if modified or interrupted
    """
    if single:
        return None

    # Build and send prompt using workset content directly
    prompt = build_request_analysis_prompt(request)
    try:
        response = progress_send_message(prompt)
    except KeyboardInterrupt:
        console = Console()
        console.print("\n[yellow]Request cancelled by user[/yellow]")
        return None

    # Early return if response is empty
    if not response:
        return None

    # Parse and handle options
    options = parse_analysis_options(response)
    if not options:
        return None

    if pre_select:
        return options.get(pre_select.upper())

    # Display formatted analysis in terminal mode
    format_analysis(response, config.raw)

    # Get user selection with validation
    selection = get_option_selection(options)
    if selection is None:
        return None

    return options[selection]
