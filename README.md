# Janito CLI

A CLI tool for software development tasks powered by AI.

Janito is an AI-powered assistant that helps automate common software development tasks like refactoring, documentation updates, and code optimization.


## Installation

```bash
# Install from PyPI
pip install janito

# Install from source
git clone https://github.com/joaompinto/janito.git
cd janito
pip install -e .
```

Note: Requires Python 3.8 or higher.


## Configuration

### API Key Setup
Janito requires an Anthropic API key to function. Set it as an environment variable:

```bash
export ANTHROPIC_API_KEY='your-api-key-here'
```

You can also add this to your shell profile (~/.bashrc, ~/.zshrc, etc.) for persistence.


### Debug Mode
Enable debug mode for detailed logging:

```bash
janito ./myproject "request" --debug
```

## Usage

```bash
janito REQUEST [OPTIONS]
```

### Arguments

- `REQUEST`: The modification request (required)

### Options

- `-w, --workdir PATH`: Working directory (defaults to current directory)
- `--raw`: Print raw response instead of markdown format
- `--play PATH`: Replay a saved prompt file
- `-i, --include PATH`: Additional paths to include in analysis (can be specified multiple times)
- `--debug`: Show debug information

### Examples

```bash
Common use cases:

```bash
# Generate documentation
janito "create docstrings for all functions"

# Implement new features
janito "add input validation to user_login function"

# Code review and improvements
janito "review code for security issues"


# Basic usage (uses current directory)
janito "add error handling"

# Specify working directory
janito "add error handling" -w ./myproject

# Include additional paths in analysis
janito "update tests" -i ./tests -i ./lib

# Show raw output
janito "refactor code" --raw

# Replay saved prompt
janito "update docs" --play .janito/history/20240101_123456_selected_.txt

# Enable debug mode
janito "optimize code" --debug
```

## Features

- AI-powered code analysis and modifications
- Support for multiple file types
- Syntax validation for Python files
- Interactive change preview and confirmation
- History tracking of all changes
- Debug mode for detailed logging

## Requirements

- Python 3.8+
- Anthropic API key