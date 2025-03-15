# Developer Guide for Janito

This document provides instructions for developers working with Janito, including installation from source and using hatch for development.

## Installing from Source

```bash
# Clone the repository
git clone https://github.com/joaompinto/janito.git
cd janito

# Install the package
pip install -e .
```

## Using hatch for Development and Build Process

This section describes how to use [hatch](https://hatch.pypa.io/) - a modern, extensible Python project manager - for the development and build process of Janito.

## What is hatch?

`hatch` is a modern Python project management tool that handles everything from project creation to publishing. It offers:

- Standardized build system with PEP 517 compliance
- Dependency management and virtual environment handling
- Project versioning and publishing tools
- Extensible plugin system
- Reproducible environments

## Setup Development Environment

### Installing hatch

First, install `hatch` following the [official installation instructions](https://hatch.pypa.io/latest/install/):

```bash
# Using pip
pip install hatch

# Or using pipx (recommended)
pipx install hatch
```

### Creating a Virtual Environment

Create and activate a virtual environment using `hatch`:

```bash
# Create and enter a virtual environment with all dependencies installed
hatch shell

# Alternatively, you can use a traditional approach
python -m venv .venv

# Activate the virtual environment
# On Unix/macOS
source .venv/bin/activate

# On Windows
.venv\Scripts\activate
```

### Installing Dependencies

Install the project dependencies using `hatch`:

```bash
# Install dependencies from pyproject.toml
pip install -e .

# Or use hatch to manage the environment with all dependencies
hatch env create
```

## Managing Dependencies

### Adding New Dependencies

To add a new dependency:

1. Add it to the `dependencies` list in `pyproject.toml`
2. Update your environment:

```bash
pip install -e .
# Or with hatch
hatch env update
```

### Managing Development Dependencies

You can define development dependencies in your pyproject.toml:

```toml
[tool.hatch.envs.dev]
dependencies = [
  "pytest",
  "pytest-cov",
]
```

And then use them with:

```bash
hatch env run -e dev pytest
```

## Building the Package

Build the package using hatch:

```bash
# Build the package (creates sdist and wheel in dist/)
hatch build
```

## Running Tests

If you have tests, you can run them with:

```bash
# Assuming you have a dev environment with pytest
hatch run test:pytest

# Or directly
hatch run test:cov
```

## CI/CD Integration

For CI/CD pipelines, use `hatch` for consistent builds:

```yaml
# Example GitHub Actions step
- name: Install dependencies and build
  run: |
    pip install hatch
    hatch build
```

## Benefits of Using hatch

- **Complete Solution**: Handles the entire project lifecycle
- **Environment Management**: Sophisticated environment management with matrix support
- **Build System**: Standardized build system with PEP 517 compliance
- **Extensibility**: Plugin system for custom functionality
- **Simplicity**: Reduces boilerplate and configuration complexity

## Troubleshooting

If you encounter any issues with `hatch`:

- Check the [hatch documentation](https://hatch.pypa.io/)
- Use the `--verbose` flag for more detailed output
- Make sure your `hatch` installation is up to date

For project-specific issues, please open an issue on the GitHub repository.