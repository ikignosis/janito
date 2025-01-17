# Janito

[![PyPI version](https://badge.fury.io/py/janito.svg)](https://badge.fury.io/py/janito)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

AI-powered CLI tool for code modifications and analysis. Janito helps you modify, analyze, and understand your codebase using natural language commands.

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Usage](#usage)
  - [Basic Commands](#basic-commands)
  - [Examples](#examples)
- [Configuration](#configuration)
- [Development](#development)
- [License](#license)

## Features

- 🤖 AI-powered code analysis and modifications (Claude AI)
- 🔄 Incremental code changes with search/replace operations
- 🎯 Precise text modifications with context matching
- 💬 Natural language interface for code operations
- 🔍 Interactive code exploration
- 📝 Automatic documentation generation
- ⚡ Fast and efficient codebase navigation
- 💾 Smart Claude AI prompt caching for faster responses

## Installation

### Prerequisites

- Python 3.8 or higher
- Anthropic API key (with smart caching to reduce API costs)

### Install via pip

```bash
pip install janito
```

### Set up API key

```bash
export ANTHROPIC_API_KEY=your_api_key_here
```

## Usage

### Basic Commands

Janito supports incremental code changes through precise text operations:
- Search and replace with context matching
- Delete specific code blocks
- File operations (create, replace, rename, move, remove)

```bash
# Modify code with natural language
janito "add docstrings to this file"

# Ask questions about the codebase
janito --ask "explain the main function in this file"

# Preview files that would be analyzed
janito --scan
```

### Examples

1. Add documentation to a file:
```bash
janito "add docstrings to all functions in src/main.py"
```

2. Analyze code structure:
```bash
janito --ask "what are the main classes in this project?"
```

3. Refactor code:
```bash
janito "convert this function to use async/await"
```

4. Generate tests:
```bash
janito "create unit tests for the User class"
```

## Configuration

### Environment Variables

- `ANTHROPIC_API_KEY`: Anthropic API key for Claude AI
- `JANITO_TEST_CMD`: Default test command to run after changes

### Command Line Options

- `-w, --workspace_dir`: Set working directory
- `-i, --include`: Additional paths to include
- `--debug`: Show debug information
- `--verbose`: Show verbose output
- `--auto-apply`: Apply changes without confirmation

## Development

### Setting up Development Environment

```bash
# Clone the repository
git clone https://github.com/joaompinto/janito.git
cd janito

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install development dependencies
pip install -e ".[dev]"
```

### Running Tests

```bash
pytest
```

### Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

MIT License - see [LICENSE](LICENSE)
