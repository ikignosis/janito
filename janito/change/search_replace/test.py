import unittest
from pathlib import Path
from .core import SearchReplacer, PatternNotFoundException

class TestSearchReplacer(unittest.TestCase):
    def test_basic_search_replace(self):
        source = "def test():\n    print('hello')"
        search = "print('hello')"
        replace = "print('world')"

        replacer = SearchReplacer(source, search, replace)
        result = replacer.replace()

        self.assertEqual(result, "def test():\n    print('world')")

    def test_indentation_aware_replace(self):
        source = """def test():
    if True:
        print('hello')
        print('world')"""
        search = """    if True:
        print('hello')
        print('world')"""
        replace = """if condition:
    print('changed')"""

        replacer = SearchReplacer(source, search, replace)
        result = replacer.replace()

        expected = """def test():
    if condition:
        print('changed')"""
        self.assertEqual(result, expected)

    def test_pattern_not_found(self):
        source = "def test():\n    print('hello')"
        search = "not_found()"
        replace = "something()"

        replacer = SearchReplacer(source, search, replace)
        with self.assertRaises(PatternNotFoundException):
            replacer.replace()

    def test_partial_match(self):
        source = "def test():\n    print('hello world')"
        search = "print('hello"  # Partial match
        replace = "print('hi"

        replacer = SearchReplacer(source, search, replace, allow_partial=True)
        result = replacer.replace()

        self.assertEqual(result, "def test():\n    print('hi world')")

if __name__ == '__main__':
    unittest.main()