import pytest
from janito.text_finder.finder import (
    ExactMatchStrategy, IndentationMatchStrategy, 
    Finder, Replacer, MatchResult
)

def test_exact_match_strategy():
    source = ["def foo():", "    pass", "    return None"]
    pattern = ["def foo():", "    pass"]
    
    result = ExactMatchStrategy.find(source, pattern)
    
    assert result is not None
    assert result.start == 0
    assert result.end == 2
    assert result.strategy == 'exact'
    assert source[result.start:result.end] == pattern

def test_exact_match_strategy_no_match():
    source = ["def foo():", "    pass", "    return None"]
    pattern = ["def bar():", "    pass"]
    
    result = ExactMatchStrategy.find(source, pattern)
    
    assert result is None

def test_indentation_match_strategy():
    source = [
        "def foo():",
        "        pass",
        "        return None"
    ]
    pattern = [
        "def foo():",
        "    pass"
    ]
    
    result = IndentationMatchStrategy.find(source, pattern)
    
    assert result is not None
    assert result.start == 0
    assert result.end == 2
    assert result.strategy == 'indentation'

def test_replacer():
    replacer = Replacer()
    source = ["def foo():", "    pass", "    return None"]
    match = MatchResult(0, 2, 'exact')
    replacement = ["def bar():", "    pass"]
    
    result = replacer.replace(source, match, replacement)
    
    assert result == [
        "def bar():",
        "    pass",
        "    return None"
    ]

def test_replacer_with_indentation():
    replacer = Replacer()
    source = ["def foo():", "        pass", "        return None"]
    match = MatchResult(0, 2, 'indentation')
    replacement = ["def bar():", "    pass"]
    
    result = replacer.replace(source, match, replacement)
    
    assert result == [
        "def bar():",
        "    pass",  # Should use replacement's indent
        "        return None"
    ]

# ...rest of tests following same pattern...
from janito.text_finder.finder import (
    ExactMatchStrategy, IndentationMatchStrategy, 
    Finder, Replacer, MatchResult
)

# Unit tests for individual components
def test_exact_match_strategy():
    source = ["def foo():", "    pass", "    return None"]
    pattern = ["def foo():", "    pass"]
    
    result = ExactMatchStrategy.find(source, pattern)
    
    assert result is not None
    assert result.start == 0
    assert result.end == 2
    assert result.strategy == 'exact'
    assert source[result.start:result.end] == pattern

def test_exact_match_strategy_no_match():
    source = ["def foo():", "    pass"]
    pattern = ["def bar():", "    pass"]
    
    result = ExactMatchStrategy.find(source, pattern)
    assert result is None

def test_indentation_match_strategy():
    source = [
        "def foo():",
        "        pass",
        "        return None"
    ]
    pattern = [
        "def foo():",
        "    pass"
    ]
    
    result = IndentationMatchStrategy.find(source, pattern)
    
    assert result is not None
    assert result.start == 0
    assert result.end == 2
    assert result.strategy == 'indentation'

def test_indentation_match_different_levels():
    source = [
        "class Test:",
        "            def test():",
        "                pass"
    ]
    pattern = [
        "class Test:",
        "    def test():",
        "        pass"
    ]
    
    result = IndentationMatchStrategy.find(source, pattern)
    
    assert result is not None
    assert result.start == 0
    assert result.end == 3
    assert result.strategy == 'indentation'

def test_finder():
    finder = Finder()
    source = ["def foo():", "    pass", "    return None"]
    pattern = ["def foo():", "    pass"]
    
    result = finder.find(source, pattern, "python")
    
    assert result is not None
    assert result.start == 0
    assert result.end == 2

def test_replacer():
    replacer = Replacer()
    source = ["def foo():", "    pass", "    return None"]
    match = MatchResult(0, 2, 'exact')
    replacement = ["def bar():", "    pass"]  # Note: includes colon
    
    result = replacer.replace(source, match, replacement)
    
    assert result == [
        "def bar():",  # Fixed: added colon to match replacement
        "    pass",
        "    return None"
    ]

def test_replacer_with_indentation():
    replacer = Replacer()
    source = ["def foo():", "        pass", "        return None"]
    match = MatchResult(0, 2, 'indentation')
    # Note: replacement has 4 spaces indentation
    replacement = ["def bar():", "    pass"]
    
    result = replacer.replace(source, match, replacement)
    
    # Result should use replacement's indentation pattern (4 spaces), 
    # not source's indentation pattern (8 spaces)
    assert result == [
        "def bar():",
        "    pass",      # Should use replacement's 4-space indent
        "        return None"
    ]

def test_replacer_with_indentation_multiple_levels():
    replacer = Replacer()
    source = ["class Test:", "            def test():", "                pass"]
    match = MatchResult(0, 3, 'indentation')
    # Replacement defines its own indentation pattern
    replacement = ["class NewTest:", "    def new_test():", "        pass"]
    
    result = replacer.replace(source, match, replacement)
    
    # Result should follow replacement's indentation pattern (4/8 spaces)
    assert result == [
        "class NewTest:",
        "    def new_test():",  # 4 spaces as defined in replacement
        "        pass"          # 8 spaces as defined in replacement
    ]
