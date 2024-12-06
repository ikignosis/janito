import pytest
from janito.prompts import (
    build_request_analysis_prompt,
    build_selected_option_prompt,
    parse_options,
    SYSTEM_PROMPT
)

def test_parse_options():
    """Test parsing options from response text"""
    response = """=== **Option 1**: Create tests
- Add unit tests
- Setup fixtures

=== **Option 2**: Update documentation
- Add docstrings
- Update README"""

    options = parse_options(response)
    
    assert len(options) == 2
    assert "Create tests" in options[1]
    assert "Update documentation" in options[2]
    assert "Add unit tests" in options[1]

def test_build_request_analysis_prompt():
    """Test building analysis prompt"""
    files_content = "test content"
    request = "create tests"
    
    prompt = build_request_analysis_prompt(files_content, request)
    
    assert "test content" in prompt
    assert "create tests" in prompt
    assert "<files>" in prompt
    assert "</files>" in prompt

def test_build_selected_option_prompt():
    """Test building selected option prompt"""
    initial_response = """=== **Option 1**: Test option
- Detail 1
- Detail 2"""
    
    prompt = build_selected_option_prompt(
        1,
        "test request",
        initial_response,
        "test files"
    )
    
    assert "test request" in prompt
    assert "Test option" in prompt
    assert "test files" in prompt

def test_system_prompt():
    """Test system prompt content"""
    assert SYSTEM_PROMPT is not None
    assert isinstance(SYSTEM_PROMPT, str)
    assert len(SYSTEM_PROMPT) > 0