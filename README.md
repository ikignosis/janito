# Janito

[![PyPI version](https://badge.fury.io/py/janito.svg)](https://badge.fury.io/py/janito)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

AI-powered CLI tool for code modifications and analysis. Janito helps you modify, analyze, and understand your codebase using natural language commands.

## Features

- Code modifications using natural language requests
- Codebase analysis and question answering
- Interactive TUI mode for better visualization
- File scanning and preview capabilities
- Git-aware operations

## Installation

### Prerequisites

- Python 3.8 or higher
- pip package manager
- An Anthropic API key (default) or OpenAI API key

### Steps

1. Install using pip:
```bash
pip install janito
```

2. Configure your API key:

For Anthropic Claude (default):
```bash
export ANTHROPIC_API_KEY=your_api_key_here
```

For OpenAI:
```bash
export OPENAI_API_KEY=your_api_key_here
export AI_BACKEND=openai
```

## Usage Examples

### Basic Commands

```bash
# Modify code
janito "add docstrings to this file"

# Ask questions about the codebase
janito --ask "explain the main function in this file"

# Preview files that would be analyzed
janito --scan

# Use interactive TUI mode
janito "refactor this code" --tui
```

### Common Use Cases

1. Code Documentation:
```bash
janito "add type hints to all functions"
janito "improve docstrings with more details"
```

2. Code Analysis:
```bash
janito --ask "what are the main classes in this project?"
janito --ask "explain the error handling flow"
```

3. Code Refactoring:
```bash
janito "convert this class to use dataclasses"
janito "split this large function into smaller ones"
```

## Configuration

### Environment Variables

- `ANTHROPIC_API_KEY`: Anthropic API key
- `OPENAI_API_KEY`: OpenAI API key (if using OpenAI backend)
- `AI_BACKEND`: AI provider ('claudeai' or 'openai')
- `JANITO_TEST_CMD`: Default test command to run after changes

### Command Line Options

- `-w, --workdir`: Set working directory
- `-i, --include`: Additional paths to include
- `--debug`: Show debug information
- `--verbose`: Show verbose output
- `--tui`: Use terminal user interface
- `--auto-apply`: Apply changes without confirmation

## Troubleshooting

### Common Issues

1. API Key Issues:
```bash
# Verify API key is set
echo $ANTHROPIC_API_KEY

# Temporarily set API key for single command
ANTHROPIC_API_KEY=your_key janito "your request"
```

2. Path Issues:
```bash
# Use absolute paths if having issues with relative paths
janito -w /full/path/to/project "your request"

# Specify additional paths explicitly
janito -i ./src -i ./tests "your request"
```

3. Debug Mode:
```bash
# Enable debug output for troubleshooting
janito --debug "your request"
```

### Error Messages

- "No command given": Provide a change request or command
- "No input provided": Check if using --input mode correctly
- "Duplicate path provided": Remove duplicate paths from includes

## License

MIT License - see [LICENSE](LICENSE)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.