import pytest
# ...existing code remains the same since FindReplacer abstracts the MatchResult details...
from janito.text_finder.finder import FindReplacer

# Basic functionality tests
def test_find_replacer_simple():
    source = """def old_function():
    print("old")
    return True"""
    
    find = """def old_function():
    print("old")"""
    
    replace = """def new_function():
    print("new")"""
    
    replacer = FindReplacer()
    result = replacer.replace(source, find, replace)
    
    assert result == """def new_function():
    print("new")
    return True"""

def test_find_replacer_indentation():
    source = """class Test:
    def old_method():
        pass"""
        
    find_pattern = """\
    def old_method():
        pass"""
        
    replacement = """\
    def new_method():
        print("new")
        return None"""
        
    find_replacer = FindReplacer()
    result = find_replacer.replace(source, find_pattern, replacement)
    
    # Normalize whitespace before comparison
    def normalize(text):
        return '\n'.join(line.rstrip() for line in text.splitlines())
        
    assert normalize(result) == normalize("""class Test:
    def new_method():
        print("new")
        return None""")

def test_find_replacer_not_found():
    source = "def test(): pass"
    find = "def missing(): pass"
    replace = "def new(): pass"
    
    replacer = FindReplacer()
    with pytest.raises(ValueError, match="Pattern not found in source"):
        replacer.replace(source, find, replace)

# End-to-end transformation tests
def test_replace_function():
    source = """def old_function(x, y):
    result = x + y
    return result

value = old_function(1, 2)"""
    
    find = """def old_function(x, y):
    result = x + y
    return result"""
    
    replace = """def new_function(a, b):
    return a + b"""
    
    replacer = FindReplacer()
    result = replacer.replace(source, find, replace)
    
    assert result == """def new_function(a, b):
    return a + b

value = old_function(1, 2)"""

def test_replace_method_in_class():
    source = """class MyClass:
    def old_method(self):
        print('old')
        return None

    def other_method(self):
        pass"""
            
    find = """    def old_method(self):
        print('old')
        return None"""
            
    replace = """    def new_method(self):
        return 'new'"""
        
    replacer = FindReplacer()
    result = replacer.replace(source, find, replace)
    
    assert result == """class MyClass:
    def new_method(self):
        return 'new'

    def other_method(self):
        pass"""

def test_replace_nested_if_block():
    source = """def process(data):
    if data:
        if isinstance(data, list):
            return len(data)
        else:
            return 0
    return None"""
    
    find = """        if isinstance(data, list):
            return len(data)
        else:
            return 0"""
    
    replace = """        return len(data) if isinstance(data, list) else 0"""
    
    replacer = FindReplacer()
    result = replacer.replace(source, find, replace)
    
    assert result == """def process(data):
    if data:
        return len(data) if isinstance(data, list) else 0
    return None"""

def test_replace_with_complex_indentation():
    source = """class TestCase:
    def test_feature(self):
        with self.assertRaises(ValueError):
            if condition:
                raise ValueError
            else:
                pass
        self.assertTrue(True)"""
    
    find = """            if condition:
                raise ValueError
            else:
                pass"""
    
    replace = """            if not condition:
                return
            raise ValueError"""
    
    replacer = FindReplacer()
    result = replacer.replace(source, find, replace)
    
    assert result == """class TestCase:
    def test_feature(self):
        with self.assertRaises(ValueError):
            if not condition:
                return
            raise ValueError
        self.assertTrue(True)"""