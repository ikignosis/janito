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

## Building and Installing

- To build the project:
  ```sh
  python -m build
  ```
- To install in editable mode:
  ```sh
  pip install -e .
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

**Requirements**: Make sure you have `build` and `twine` installed:
```sh
pip install build twine
```

## Running Tests

- (Add test instructions here if/when tests are present)

## Contributing

- Follow PEP8 and use [ruff](https://github.com/charliermarsh/ruff) for linting.
- Document all public functions and classes.
- Update this README-dev.md as needed for developer-facing changes.

---
For more information, see the main `README.md` or contact the maintainers.

