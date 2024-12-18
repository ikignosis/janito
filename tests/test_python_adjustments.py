import pytest
from janito.search_replace import SearchReplacer

def test_function_definition_adjustment():
    source = '''def old_function(a, b):
    print("hello")
    return a + b'''
    
    pattern = '''def old_function(a, b):
    print("hello")
    return a + b'''
    
    replacement = '''def new_function(x, y):
    print("world")
    return x * y'''
    
    replacer = SearchReplacer(source, pattern, replacement, '.py')
    result = replacer.replace()
    assert result == '''def new_function(x, y):
    print("world")
    return x * y'''

def test_nested_indentation_adjustment():
    source = '''class MyClass:
    def method(self):
        if condition:
            print("nested")
            return True
        return False'''
    
    pattern = '''    def method(self):
        if condition:
            print("nested")
            return True'''
    
    replacement = '''    def method(self):
        if True:
            print("always")
            return False'''
    
    replacer = SearchReplacer(source, pattern, replacement, '.py')
    result = replacer.replace()
    assert result == '''class MyClass:
    def method(self):
        if True:
            print("always")
            return False
        return False'''

def test_partial_block_replacement():
    source = '''def process():
    # Step 1
    data = prepare()
    # Step 2
    result = transform(data)
    # Step 3
    save(result)'''
    
    pattern = '''    # Step 2
    result = transform(data)'''
    
    replacement = '''    # Step 2 - Enhanced
    result = enhanced_transform(data)
    validate(result)'''
    
    replacer = SearchReplacer(source, pattern, replacement, '.py')
    result = replacer.replace()
    assert result == '''def process():
    # Step 1
    data = prepare()
    # Step 2 - Enhanced
    result = enhanced_transform(data)
    validate(result)
    # Step 3
    save(result)'''

def test_method_with_decorators():
    source = '''class API:
    @route("/endpoint")
    @authenticate
    def handler(self, request):
        process(request)
        return response'''
    
    pattern = '''    @route("/endpoint")
    @authenticate
    def handler(self, request):
        process(request)'''
    
    replacement = '''    @route("/new/endpoint")
    @validate
    @authenticate
    def handler(self, request):
        validate(request)
        process(request)'''
    
    replacer = SearchReplacer(source, pattern, replacement, '.py')
    result = replacer.replace()
    assert result == '''class API:
    @route("/new/endpoint")
    @validate
    @authenticate
    def handler(self, request):
        validate(request)
        process(request)
        return response'''

def test_complex_indentation_patterns():
    source = '''def outer():
    try:
        with context() as ctx:
            if condition:
                for item in items:
                    process(item)
            else:
                skip()
    except Error:
        handle()'''
    
    pattern = '''            if condition:
                for item in items:
                    process(item)
            else:
                skip()'''
    
    replacement = '''            for item in items:
                if condition(item):
                    process(item)
                else:
                    skip(item)'''
    
    replacer = SearchReplacer(source, pattern, replacement, '.py')
    result = replacer.replace()
    assert result == '''def outer():
    try:
        with context() as ctx:
            for item in items:
                if condition(item):
                    process(item)
                else:
                    skip(item)
    except Error:
        handle()'''

def test_blank_line_preservation():
    source = '''def function():
    # First block
    step1()
    step2()

    # Second block
    step3()
    step4()'''
    
    pattern = '''    # First block
    step1()
    step2()'''
    
    replacement = '''    # Updated block
    new_step1()
    new_step2()'''
    
    replacer = SearchReplacer(source, pattern, replacement, '.py')
    result = replacer.replace()
    assert result == '''def function():
    # Updated block
    new_step1()
    new_step2()

    # Second block
    step3()
    step4()'''

def test_mixed_indentation_styles():
    # Source uses tabs, but we'll represent it with spaces in the string
    source = '''class Mixed:
    def tabs(self):
        return True
    def spaces(self):
        return True'''
    
    pattern = '''    def tabs(self):
        return True'''
    
    replacement = '''    def consistent(self):
        return True'''
    
    replacer = SearchReplacer(source, pattern, replacement, '.py')
    result = replacer.replace()
    
    # Expected output should have consistent 4-space indentation
    expected = '''class Mixed:
    def consistent(self):
        return True
    def spaces(self):
        return True'''
        
    assert result == expected

def test_inline_comment_preservation():
    source = '''def process():
    value = 1  # Initial value
    result = value * 2  # Double it
    return result  # Final result'''
    
    pattern = '''    value = 1  # Initial value
    result = value * 2  # Double it'''
    
    replacement = '''    value = 100  # New initial value
    result = value + 50  # Add bonus'''
    
    replacer = SearchReplacer(source, pattern, replacement, '.py')
    result = replacer.replace()
    assert result == '''def process():
    value = 100  # New initial value
    result = value + 50  # Add bonus
    return result  # Final result'''

def test_multiline_string_handling():
    source = '''def docs():
    return """
    This is a
    multiline
    docstring
    """'''
    
    pattern = '''    return """
    This is a
    multiline
    docstring
    """'''
    
    replacement = '''    return """
    Updated
    docstring
    content
    """'''
    
    replacer = SearchReplacer(source, pattern, replacement, '.py')
    result = replacer.replace()
    assert result == '''def docs():
    return """
    Updated
    docstring
    content
    """'''
