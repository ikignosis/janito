# Using the Development Version

This guide explains how to install and use the latest development version of this project directly from GitHub.

## Installation from GitHub Main Branch

To install the latest development version of this project directly from the GitHub main branch, run:

```bash
pip install git+https://github.com/joaompinto/janito.git@main
```

Replace `<your-org-or-username>` and `<repo-name>` with the appropriate values for this repository.

## Editable Install (for Development)

If you want to make changes to the code and have them reflected immediately (without reinstalling), use an editable install:

```bash
git clone https://github.com/joaompinto/janito.git
cd <repo-name>
git checkout main
pip install -e .
```

This will install the package in "editable" mode, so changes to the source code are immediately available in your environment.

## Notes

- Always ensure you are on the correct branch (e.g., `main`) for the latest development version.
- For further development setup (linting, pre-commit hooks, etc.), see the [Developer Guide](README_DEV.md).
