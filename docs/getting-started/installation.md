# Installation

This guide covers how to install janito.

## From PyPI

The easiest way to install janito is from PyPI:

```bash
pip install janito
```

## From Source

For development or the latest features, install from source:

### Prerequisites

- Python 3.10+
- Git
- GitHub CLI (optional)

### Clone and Install

```bash
# Clone the repository
git clone https://github.com/ikignosis/janito.git
cd janito

# Install dependencies
pip install -r requirements.txt

# Install in development mode
pip install -e .
```

### Running Without Installation

You can also run janito directly without installing:

```bash
python -m janito "Your prompt here"
```

## Verify Installation

Check that janito is installed correctly:

```bash
janito --version
```

Or run the help command:

```bash
janito --help
```

## Dependencies

janito requires the following dependencies:

| Package | Version | Purpose |
|---------|---------|---------|
| `openai` | >=1.0.0 | OpenAI API client |
| `rich` | >=10.0.0 | Rich terminal output |
| `prompt-toolkit` | >=3.0.0 | Interactive shell |
| `requests` | >=2.28.0 | HTTP library (MCP support) |
| `pathspec` | >=0.11.0 | `.gitignore`-aware file listing |

These are automatically installed when you install `janito`.

## System Requirements

- **Operating System**: Windows, macOS, Linux
- **Python**: 3.10, 3.11, 3.12, 3.13, 3.14
- **Terminal**: Any modern terminal (PowerShell, Bash, Zsh, etc.)

## Next Steps

Now that janito is installed, head to the [Quick Start](quick-start.md) guide to configure and run your first prompt.
