#!/usr/bin/env python3
"""
Example test file to demonstrate basic testing functionality.
This file contains simple test cases that can be run with pytest.
"""

import pytest
import os
import sys


def test_basic_assertion():
    """Test that basic assertions work correctly."""
    assert True
    assert 1 + 1 == 2
    assert "hello" == "hello"


def test_string_operations():
    """Test string operations."""
    text = "Hello, World!"
    assert text.upper() == "HELLO, WORLD!"
    assert text.lower() == "hello, world!"
    assert text.startswith("Hello")
    assert text.endswith("World!")


def test_list_operations():
    """Test list operations."""
    numbers = [1, 2, 3, 4, 5]
    assert len(numbers) == 5
    assert sum(numbers) == 15
    assert 3 in numbers
    assert 6 not in numbers


def test_dictionary_operations():
    """Test dictionary operations."""
    person = {"name": "John", "age": 30, "city": "New York"}
    assert person["name"] == "John"
    assert person.get("age") == 30
    assert "city" in person
    assert person.get("country", "Unknown") == "Unknown"


def test_file_existence():
    """Test that this test file exists."""
    current_file = __file__
    assert os.path.exists(current_file)
    assert os.path.isfile(current_file)


def test_python_version():
    """Test Python version compatibility."""
    assert sys.version_info.major >= 3
    assert sys.version_info.minor >= 6


class TestCalculator:
    """Test class for calculator functionality."""

    def test_addition(self):
        """Test addition operation."""
        assert 2 + 2 == 4
        assert -1 + 1 == 0
        assert 0 + 0 == 0

    def test_subtraction(self):
        """Test subtraction operation."""
        assert 5 - 3 == 2
        assert 0 - 5 == -5
        assert 10 - 10 == 0

    def test_multiplication(self):
        """Test multiplication operation."""
        assert 3 * 4 == 12
        assert 0 * 5 == 0
        assert -2 * 3 == -6

    def test_division(self):
        """Test division operation."""
        assert 10 / 2 == 5
        assert 1 / 1 == 1
        with pytest.raises(ZeroDivisionError):
            1 / 0


if __name__ == "__main__":
    # Run tests when executed directly
    pytest.main([__file__, "-v"])
