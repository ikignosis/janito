# Development

This section covers development setup and contribution guidelines.

## Topics

- [Contributing](contributing.md) - How to contribute to janito

## Prerequisites

- Python 3.6+
- Git
- GitHub CLI (optional)

## Quick Setup

```bash
# Clone the repository
git clone https://github.com/ikignosis/janito.git
cd janito

# Install dependencies
pip install -r requirements.txt

# Install in development mode
pip install -e .
```

## Running from Source

```bash
python -m janito --config
python -m janito "Hello"
```

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=janito

# Run specific test file
pytest tests/test_core.py
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
