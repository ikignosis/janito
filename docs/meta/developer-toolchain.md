# Developer Toolchain Guide

For tool development, see the [Tools Developer Guide](../guides/tools-developer-guide.md).

## Code Style, Linting, and Pre-commit Hooks

This project uses [pre-commit](https://pre-commit.com/) to enforce code style and linting automatically using [Black](https://black.readthedocs.io/en/stable/) (formatter) and [Ruff](https://docs.astral.sh/ruff/) (linter).

### Setup

1. Install pre-commit if you haven't already:

```bash
uv pip install pre-commit
```

2. Install the hooks:

```bash
pre-commit install
```

### Usage

- Hooks will run automatically on `git commit`.
- To manually check all files:

```bash
pre-commit run --all-files
```

- If any issues are found, pre-commit will attempt to fix them or display errors to resolve.

### Notes

- Always run the hooks before pushing code to ensure consistent style and linting.
- See `.pre-commit-config.yaml` for configuration details.

---
