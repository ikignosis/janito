# Janito

[![PyPI version](https://badge.fury.io/py/janito.svg)](https://badge.fury.io/py/janito)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

AI-powered CLI tool for code modifications and analysis. Janito helps you modify, analyze, and understand your codebase using natural language commands.

## Installation

Requires Python 3.8+ and an Anthropic API key.

```bash
pip install janito
export ANTHROPIC_API_KEY=your_api_key_here
```

## Usage

```bash
# Modify code
janito "add docstrings to this file"

# Ask questions about the codebase
janito --ask "explain the main function in this file"

# Preview files that would be analyzed
janito --scan

# Start interactive shell
janito
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

## License

MIT License - see [LICENSE](LICENSE)