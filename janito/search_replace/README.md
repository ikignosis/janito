# Search/Replace Module

A smart search and replace module that handles code indentation and provides debugging capabilities for failed searches.

## Usage

### As a Module

```python
from janito.search_replace import SearchReplacer

# Basic search/replace
source_code = """
def hello():
    print("Hello")
    print("World")
"""

search = """    print("Hello")
    print("World")"""

replacement = """    print("Hi")
    print("Universe")"""

replacer = SearchReplacer(source_code, search, replacement)
modified = replacer.replace()
```

### Command Line Debugging

When a search fails, a debug file is automatically created in `.janito/change_history/`. You can debug these files using:

```bash
python -m janito.search_replace <debug_file>
```

Example debug file format:
```
Test: Failed search in example.py
========================================
Original:
def hello():
    print("Hello")
    print("World")
========================================
Search pattern:
    print("Hi")
    print("World")
========================================
```

## Features

- Indentation-aware searching
- Multiple search strategies:
  - ExactMatch: Matches content with exact indentation
  - ExactContent: Matches content ignoring indentation
  - IndentAware: Matches preserving relative indentation
- Debug mode with detailed indentation analysis
- File extension specific behavior
- Automatic debug file generation for failed searches

## Search Strategies

The module uses multiple search strategies in a fallback chain to find the best match:

### ExactMatch Strategy
- Matches content exactly, including all whitespace and indentation
- Strictest matching strategy
- Example:
  ```python
  # Pattern:
      def hello():
          print("Hi")
  
  # Will only match exact indentation:
      def hello():
          print("Hi")
  ```

### IndentAware Strategy
- Preserves relative indentation between lines
- Allows different base indentation levels
- Example:
  ```python
  # Pattern:
      print("Hello")
      print("World")
  
  # Matches with different base indentation:
  def test():
      print("Hello")
      print("World")
  
  def other():
          print("Hello")
          print("World")
  ```

### ExactContent Strategy
- Ignores all indentation
- Matches content after stripping whitespace
- Most flexible strategy
- Example:
  ```python
  # Pattern:
  print("Hello")
      print("World")
  
  # Matches regardless of indentation:
        print("Hello")
    print("World")
  ```

### ExactContentNoComments Strategy
- Ignores indentation, comments, and empty lines
- Most flexible strategy
- Example:
  ```python
  # Pattern:
  print("Hello")  # greeting
  
  print("World")  # message

  # Matches:
  def test():
        print("Hello")   # different comment
        # some comment
        print("World")
  ```

### Strategy Selection
- Strategies are tried in order: ExactMatch → IndentAware → ExactContent → ExactContentNoComments
- File extension specific behavior:
  - Python files (.py): All strategies
  - Java files (.java): All strategies
  - JavaScript/TypeScript (.js/.ts): All strategies
  - Other files: ExactMatch, ExactContent, and ExactContentNoComments

## Debug Output

When debugging failed searches, the module provides:
- Visual whitespace markers (· for spaces, → for tabs)
- Indentation analysis
- Line-by-line matching attempts
- Strategy selection information
