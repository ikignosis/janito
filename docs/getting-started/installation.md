# Installation

This guide covers how to install Janito4.

## From PyPI

The easiest way to install Janito4 is from PyPI:

```bash
pip install janito4
```

## From Source

For development or the latest features, install from source:

### Prerequisites

- Python 3.6+
- Git
- GitHub CLI (optional)

### Clone and Install

```bash
# Clone the repository
git clone https://github.com/ikignosis/janito4.git
cd janito4

# Install dependencies
pip install -r requirements.txt

# Install in development mode
pip install -e .
```

### Running Without Installation

You can also run Janito4 directly without installing:

```bash
python -m janito4 "Your prompt here"
```

## Verify Installation

Check that Janito4 is installed correctly:

```bash
janito4 --version
```

Or run the help command:

```bash
janito4 --help
```

## Dependencies

Janito4 requires the following dependencies:

| Package | Version | Purpose |
|---------|---------|---------|
| `openai` | >=1.0.0 | OpenAI API client |
| `rich` | >=10.0.0 | Rich terminal output |
| `prompt-toolkit` | >=3.0.0 | Interactive shell |
| `requests` | >=2.28.0 | HTTP library |

These are automatically installed when you install `janito4`.

## System Requirements

- **Operating System**: Windows, macOS, Linux
- **Python**: 3.6, 3.7, 3.8, 3.9, 3.10, 3.11+
- **Terminal**: Any modern terminal (PowerShell, Bash, Zsh, etc.)

## Next Steps

Now that Janito4 is installed, head to the [Quick Start](quick-start.md) guide to configure and run your first prompt.
