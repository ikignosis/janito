# Development Guide

This guide covers how to set up Janito4 for development.

## Prerequisites

- Python 3.6+
- Git
- GitHub CLI (optional, for cloning)

## Clone the Repository

```bash
git clone https://github.com/ikignosis/janito4.git
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

## Install Dependencies

```bash
pip install -r requirements.txt
```

## Install in Development Mode

```bash
pip install -e .
```

This installs the package in "editable" mode, so changes to the source code take effect immediately without reinstallation.

## Running from Source

You can also run the package directly without installing:

```bash
python -m janito4 --config
```

## Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=janito4

# Run specific test file
pytest tests/test_core.py
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
- [README_ENVIRONMENT.md](README_ENVIRONMENT.md) - Environment variables
