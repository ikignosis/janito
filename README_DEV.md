# Development Guide

This guide covers how to set up janito for development.

## Prerequisites

- Python 3.10+
- Git
- [uv](https://docs.astral.sh/uv/) (project & package manager)
- GitHub CLI (optional, for cloning)

## Clone the Repository

```bash
git clone https://github.com/joaompinto/janito.git
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

### Release Checklist

The changelog is enforced at two points: a local pre-commit hook (see below) and
the release GitHub workflow. Follow this checklist so the release workflow does
not fail:

1. **Update `CHANGELOG.md`** – promote the `[Unreleased]` section to the version
   you are about to tag. The fastest way is the helper script, which rewrites the
   heading and opens a fresh empty `[Unreleased]` on top:

   ```bash
   # auto-bump from the last tag (minor by default)
   uv run python scripts/promote_changelog.py            # v4.11.0 -> v4.12.0
   uv run python scripts/promote_changelog.py --bump major   # -> v5.0.0
   uv run python scripts/promote_changelog.py --dry-run      # preview, no write

   # or pin an exact version
   uv run python scripts/promote_changelog.py v5.0.0
   ```

   It turns this:

   ```markdown
   ## [Unreleased](https://github.com/joaompinto/janito/compare/v4.11.0...HEAD)
   ```

   into this (a concrete release heading plus a new empty `[Unreleased]`):

   ```markdown
   ## [Unreleased](https://github.com/joaompinto/janito/compare/v4.12.0...HEAD)

   ## [v4.12.0](https://github.com/joaompinto/janito/compare/v4.11.0...v4.12.0) - 2026-07-26
   ```

   (You can also edit the heading by hand — just make sure it reads
   `## [vX.Y.Z]` and matches the tag exactly.)

2. **Commit the changelog change** – the `changelog-freshness` pre-commit hook
   passes because `CHANGELOG.md` is staged (or was modified within the last hour).
3. **Tag and push** – create the annotated tag and push it. The release workflow
   runs `scripts/check_changelog_freshness.py` in *version mode* and fails fast
   (before building or publishing) unless `CHANGELOG.md` contains a heading for
   the exact tag, e.g. `## [v4.12.0]`. A bare `[Unreleased]` section is not enough.

> **Tip:** if you need to cut a release without a changelog entry (e.g. an
> emergency hotfix), the workflow check can be bypassed by re-running it without
> `CHANGELOG_REQUIRE_VERSION` set — but you should add the changelog entry
> immediately afterwards.

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

## Pre-commit Hooks

The project uses [pre-commit](https://pre-commit.com/) to run linting and
formatting checks (isort, black, ruff, and a set of standard hooks) before each
commit. `pre-commit` is part of the `dev` dependency group, so it is already
installed after `uv sync`.

Install the git hooks once, after cloning:

```bash
uv run pre-commit install
```

The hooks then run automatically on every `git commit`. You can also run them
manually against all files at any time:

```bash
uv run pre-commit run --all-files
```

### Changelog Freshness Hook

In addition to linting/formatting, a local hook (`changelog-freshness`) guards
the changelog. On every commit it **fails unless `CHANGELOG.md` was updated**,
which is true if *either*:

- `CHANGELOG.md` is staged for the commit (you're editing it now), **or**
- its modification time is within the last hour (tunable via
  `CHANGELOG_MAX_AGE_SECONDS`).

To bypass it for a one-off commit (use sparingly):

```bash
SKIP=changelog-freshness git commit -m "..."
# or
git commit --no-verify
```

The matching release-time guard lives in the GitHub release workflow — see the
[Release Checklist](#release-checklist) above.

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
