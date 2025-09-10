# Developer README for janito

This document provides guidelines and instructions for developers contributing to the `janito` project.

## Version Management

- The project uses [setuptools_scm](https://github.com/pypa/setuptools_scm) for automatic version management.

- Do **not** manually set the version in any Python file or in `pyproject.toml`.

- The version is derived from your latest Git tag. To update the version, create a new tag:
  ```sh
  git tag vX.Y.Z
  git push --tags
  ```

- The `__version__` attribute is available via `janito.__version__`.

## Project Structure

- Source code is in the `janito/` directory.
- Entry points and CLI are defined in `janito/__main__.py`.
- Tests should be placed in a `tests/` directory (create if missing).

## Dependencies

- Runtime dependencies are listed in `requirements.txt`.
- Development dependencies are in `requirements-dev.txt`.
- Dependencies are dynamically loaded via `pyproject.toml`.

### Virtual Environment Benefits

Using a virtual environment ensures:

- Isolated dependencies that won't conflict with system packages
- Reproducible development environment across different machines
- Easy cleanup - just delete the `venv` directory if needed
- Consistent Python version and package versions for all contributors

## Development Environment Setup

### Using Python Virtual Environment (Recommended)

1. **Create and activate a virtual environment:**
   ```sh
   # Create virtual environment
   python -m venv venv
   
   # Activate it
   source venv/bin/activate  # On Linux/Mac
   # or
   venv\Scripts\activate  # On Windows
   ```

2. **Install development dependencies:**
   ```sh
   # Install the package in editable mode with dev dependencies
   uv pip install -e ".[dev]"
   ```

3. **Verify installation:**
   ```sh
   python -c "import janito; print(janito.__version__)"
   ```

### Alternative: System-wide Installation

If you prefer not to use a virtual environment:

```sh
uv pip install -e ".[dev]"
```

## Building and Installing

- To build the project:
  ```sh
  python -m build
  ```

- To install in editable mode:
  ```sh
  uv pip install -e .
  ```

## Release Process

The project includes an automated release script at `tools/release.py` that handles the complete release process:

- **Full release** (build + upload to PyPI):
  ```sh
  python tools/release.py
  ```

- **Build only** (skip PyPI upload):
  ```sh
  python tools/release.py --build-only
  ```

The release script will:

1. Check for uncommitted changes
2. Verify the latest git tag version
3. Check PyPI for existing versions
4. Build the package using `python -m build`
5. Upload to PyPI using `twine upload`

Make sure you have `build` and `twine` installed:

```sh
uv pip install build twine
```

## Running Tests

- (Add test instructions here if/when tests are present)

## Development Workflow Tips

### Keeping Your Environment Clean

1. **Always activate your virtual environment before working:**
   ```sh
   source venv/bin/activate  # Linux/Mac
   venv\Scripts\activate     # Windows
   ```

2. **Update dependencies when pulling new changes:**
   ```sh
   uv pip install -e ".[dev]" --upgrade
   ```

3. **Deactivate virtual environment when done:**
   ```sh
   deactivate
   ```

### Common Virtual Environment Issues

- **"Command not found" errors**: Make sure the virtual environment is activated
- **Import errors**: Reinstall the package with `uv pip install -e ".[dev]"`
- **Permission errors**: Use virtual environment instead of system-wide installation

## Contributing

- Follow PEP8 and use [ruff](https://github.com/charliermarsh/ruff) for linting.
- Document all public functions and classes.
- Update this README-dev.md as needed for developer-facing changes.

## Quick Start Checklist

For new developers getting started:

1. **Clone the repository**
2. **Create and activate virtual environment** (see [Development Environment Setup](#development-environment-setup))
3. **Install development dependencies** with `uv pip install -e ".[dev]"`
4. **Verify installation** with `python -c "import janito; print(janito.__version__)"`
5. **Run tests** (when available) to ensure everything works
6. **Start coding!**

---

For more information, see the main `README.md` or contact the maintainers.

