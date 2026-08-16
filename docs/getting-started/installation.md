# Installation

This guide covers how to install janito.

## From PyPI

The easiest way to install janito is from PyPI:

```bash
pip install janito
```

Or, with [uv](https://docs.astral.sh/uv/) (recommended):

```bash
uv tool install janito
```

## From Source

For development or the latest features, install from source:

### Prerequisites

- Python 3.10+
- Git
- [uv](https://docs.astral.sh/uv/) (project & package manager)
- GitHub CLI (optional)

### Clone and Install

```bash
# Clone the repository
git clone https://github.com/joaompinto/janito.git
cd janito

# Create the virtual environment and install the project + dev dependencies
uv sync
```

`uv sync` installs janito in **editable mode** by default and installs the `dev`
dependency group. An editable install means your source-code changes take effect
immediately without reinstalling (the equivalent of `pip install -e .`). To also
install the documentation tooling:

```bash
uv sync --group docs
```

### Running Without Installation

You can also run janito directly from the synced environment:

```bash
uv run python -m janito "Your prompt here"
```

## Verify Installation

Check that janito is installed correctly:

```bash
uv run janito --version
```

Or run the help command:

```bash
uv run janito --help
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
