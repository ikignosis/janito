# Janito

AI-powered CLI tool for code modifications and analysis.

## Installation

```bash
# Install package
pip install janito

# Set API key
export ANTHROPIC_API_KEY=your_api_key_here
```

## Basic Usage

```bash
# Modify code
janito "add docstrings to this file"

# Ask questions
janito --ask "explain this code"

# Preview changes
janito --scan
```

## Common Options

- `-w, --workdir`: Set working directory
- `-i, --include`: Additional paths to include
- `--test`: Run tests after changes
- `--auto-apply`: Apply without confirmation

## Requirements

- Python 3.8+
- Anthropic API key

## License

MIT License - see [LICENSE](LICENSE)