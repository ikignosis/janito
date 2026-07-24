# Development

This section covers development setup and contribution guidelines.

## Topics

- [Contributing](contributing.md) - How to contribute to janito

## Prerequisites

- Python 3.10+
- Git
- [uv](https://docs.astral.sh/uv/) (project & package manager)
- GitHub CLI (optional)

## Quick Setup

```bash
# Clone the repository
git clone https://github.com/ikignosis/janito.git
cd janito

# Create the virtual environment and install the project + dev dependencies
uv sync
```

`uv sync` reads `pyproject.toml` and `uv.lock` and installs janito in **editable
mode** by default, plus the `dev` dependency group. An editable install means your
source-code changes take effect immediately (the equivalent of `pip install -e .`).

To also install the documentation tooling:

```bash
uv sync --group docs
```

## Running from Source

```bash
uv run python -m janito --config
uv run python -m janito "Hello"
```

## Testing

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=janito

# Run specific test file
uv run pytest tests/test_core.py
```

## Version Management

janito uses [setuptools-scm](https://github.com/pypa/setuptools_scm) for automatic versioning.

- Version is derived from the latest git tag
- To release a new version:
  ```bash
  git tag -a v1.0.0 -m "Release version 1.0.0"
  git push origin v1.0.0
  ```

## Code Style

- 4 spaces for indentation
- Follow PEP 8 guidelines
- Add type hints where possible
- Write docstrings for public functions/classes

## Next Steps

Read the [Contributing guide](contributing.md) to learn how to submit changes.
