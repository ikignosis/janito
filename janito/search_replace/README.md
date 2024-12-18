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

The module employs multiple search strategies in a fallback chain to find the best match. Each strategy has specific behaviors and use cases:

### ExactMatch Strategy
- Matches content exactly, including all whitespace and indentation
- Strictest matching strategy
- Best for precise replacements where indentation matters
- Example:
  ```python
  # Pattern:
      def hello():
          print("Hi")

  # Will only match exact indentation:
      def hello():
          print("Hi")

  # Won't match different indentation:
  def hello():
      print("Hi")
  ```

### IndentAware Strategy
- Preserves relative indentation between lines
- Allows different base indentation levels
- Ideal for matching code blocks inside functions/classes
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

  # Won't match if relative indentation differs:
  def wrong():
      print("Hello")
          print("World")
  ```

### ExactContent Strategy
- Ignores all indentation
- Matches content after stripping whitespace
- Useful for matching code regardless of formatting
- Example:
  ```python
  # Pattern:
  print("Hello")
      print("World")

  # Matches any indentation:
        print("Hello")
    print("World")

  # Also matches:
  print("Hello")
print("World")
  ```

### ExactContentNoComments Strategy
- Ignores indentation, comments, and empty lines
- Most flexible strategy
- Perfect for matching code with varying comments/formatting
- Example:
  ```python
  # Pattern:
  print("Hello")  # greeting

  print("World")  # message

  # Matches all these variations:
  def test():
        print("Hello")   # different comment
        # some comment
        print("World")

  # Or:
  print("Hello")  # no comment
  print("World")  # different note
  ```

### ExactContentNoCommentsFirstLinePartial Strategy
- Matches first line partially, ignoring comments
- Useful for finding code fragments or partial matches
- Example:
  ```python
  # Pattern:
  print("Hello")

  # Matches partial content:
  message = print("Hello") + "extra"
  result = print("Hello, World")
  ```

### Strategy Selection and File Types

Strategies are tried in the following order:
1. ExactMatch
2. IndentAware
3. ExactContent
4. ExactContentNoComments
5. ExactContentNoCommentsFirstLinePartial

File extension specific behavior:

| File Type | Available Strategies |
|-----------|---------------------|
| Python (.py) | All strategies |
| Java (.java) | All strategies |
| JavaScript (.js) | All strategies |
| TypeScript (.ts) | All strategies |
| Other files | ExactMatch, ExactContent, ExactContentNoComments, ExactContentNoCommentsFirstLinePartial |

The module automatically selects the appropriate strategies based on the file type and tries them in order until a match is found.

## Debug Output

When debugging failed searches, the module provides:
- Visual whitespace markers (· for spaces, → for tabs)
- Indentation analysis
- Line-by-line matching attempts
- Strategy selection information