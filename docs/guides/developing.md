# Developing & Extending Janito

This guide explains how to set up Janito for development and install the latest version from GitHub.

## Installing the Latest Development Version

To install the most recent development version from the GitHub main branch, run:

```bash
uv pip install git+git@github.com:ikignosis/janito.git@main
```

## Editable Install for Local Development

To make code changes and see them reflected immediately (without reinstalling), use an editable install:

```bash
git clone git@github.com:ikignosis/janito.git
cd janito
git checkout main
uv pip install -e .
```

This installs Janito in "editable" mode, so changes to the source code are instantly available in your environment.

## Additional Development Setup

- Ensure you are on the correct branch (e.g., `main`) for the latest development version.
- For linting, pre-commit hooks, and other developer tools, see the Developer Toolchain Guide in the meta directory.
