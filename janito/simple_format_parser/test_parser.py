import pytest
from parser import parse_document, ParserError

def test_basic_parsing():
    content = """
statement1
field1: value1
field2: value2
"""
    doc = parse_document(content)
    assert len(doc.statements) == 1
    assert doc.statements[0].name == "statement1"
    assert doc.statements[0].fields["field1"] == "value1"
    assert doc.statements[0].fields["field2"] == "value2"

def test_multiline_field():
    content = """
statement1
field1:
    .line1
    .line2
field2: value2
"""
    doc = parse_document(content)
    assert doc.statements[0].fields["field1"] == "line1\nline2\n"
    assert doc.statements[0].fields["field2"] == "value2"

def test_comments_and_empty_lines():
    content = """
statement1
field1:
    # comment
    
    .line1
field2: value2
"""
    doc = parse_document(content)
    assert doc.statements[0].fields["field1"] == "line1\n"
    assert doc.statements[0].fields["field2"] == "value2"

def test_field_with_comment():
    content = """
statement1
field1: value1 # comment
field2: value2
"""
    doc = parse_document(content)
    assert doc.statements[0].fields["field1"] == "value1"
    assert doc.statements[0].fields["field2"] == "value2" 