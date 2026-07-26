# Development Guide

This guide covers how to set up janito for development.

## Prerequisites

- Python 3.10+
- Git
- [uv](https://docs.astral.sh/uv/) (project & package manager)
- GitHub CLI (optional, for cloning)

## Clone the Repository

```bash
git clone https://github.com/ikignosis/janito.git
cd janito
```

## Version Management

The project uses [setuptools-scm](https://github.com/pypa/setuptools_scm) for automatic version management based on git tags.

- Version is automatically derived from the latest git tag
- To release a new version, create an annotated tag:
  ```bash
  git tag -a v1.0.0 -m "Release version 1.0.0"
  git push origin v1.0.0
  ```

## Install Dependencies (Editable Install)

janito uses [uv](https://docs.astral.sh/uv/) to manage the virtual environment, dependencies, and the lock file (`uv.lock`).

```bash
# Create the virtual environment and install the project + dev dependencies
uv sync
```

`uv sync` reads `pyproject.toml` and `uv.lock` and installs janito in **editable
mode** by default, plus the `dev` dependency group. An editable install means your
source-code changes take effect immediately — you never need to reinstall after
editing the code. This is the equivalent of the old `pip install -e .`.

To also install the documentation tooling:

```bash
uv sync --group docs
```

If you ever want a regular (non-editable) install instead, pass `--no-editable`:

```bash
uv sync --no-editable
```

## Common Commands

```bash
# Run the CLI
uv run janito --config

# Add a runtime dependency
uv add <package>

# Add a dev-only dependency
uv add --group dev <package>

# Update the lock file
uv lock

# Upgrade a dependency
uv lock --upgrade-package <package>
```

## Running from Source

You can also run the package directly from the synced environment:

```bash
uv run python -m janito --config
```

## Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=janito

# Run specific test file
uv run pytest tests/test_core.py
```

## Code Style

We use standard Python conventions. Key points:

- 4 spaces for indentation
- Follow PEP 8 guidelines
- Add type hints where possible
- Write docstrings for public functions/classes

## Submitting Changes

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Make your changes
4. Run tests
5. Submit a pull request

## Related Guides

- [README.md](README.md) - Main documentation
- [README_LOCAL.md](README_LOCAL.md) - Custom endpoints configuration
- [README_MCP.md](README_MCP.md) - MCP server configuration
