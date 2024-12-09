"""Core package initialization for Janito."""

from .analysis import (
    AnalysisOption,
    parse_analysis_options,
    format_analysis,
    get_history_file_type,
    get_history_path,
    get_timestamp,
    save_to_file,
    build_request_analysis_prompt,
    get_option_selection,
    prompt_user,
    validate_option_letter
)

from .change import (
    apply_single_change,
    parse_and_apply_changes_sequence,
    get_file_type,
    process_and_save_changes,
    format_parsed_changes,
    apply_content_changes,
    handle_changes_file
)

__all__ = [
    # Analysis exports
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
    'validate_option_letter',
    
    # Change exports
    'apply_single_change',
    'parse_and_apply_changes_sequence',
    'get_file_type',
    'process_and_save_changes',
    'format_parsed_changes',
    'apply_content_changes',
    'handle_changes_file'
]
