# Release Process

This document describes how to cut a new release of janito. It is the
source of truth for the manual steps; the automation that runs afterwards
is described in [.github/workflows/release.yaml](.github/workflows/release.yaml).

Releases use [Semantic Versioning](https://semver.org/spec/v2.0.0.html) with
a `v` prefix (`vMAJOR.MINOR.PATCH`, e.g. `v4.18.1`). The package version is
derived from git tags via `setuptools-scm`, so the tag **is** the release.

Prerequisites:

- Working tree on `main`, clean (no uncommitted changes).
- `uv` available (see [README_DEV.md](README_DEV.md) for setup).
- `CHANGELOG.md` has been kept up to date while developing — new entries
  go under the `## [Unreleased]` section.

The process is four steps:

1. [Determine the version](#1-determine-the-version)
2. [Run the promote_changelog script](#2-run-the-promote_changelog-script)
3. [Commit the changelog changes](#3-commit-the-changelog-changes)
4. [Tag](#4-tag)

## 1. Determine the version

Decide the bump based on what the request/release contains, and check the
latest existing tag so the next version is computed from it:

```bash
git fetch --tags --prune
git describe --tags --abbrev=0          # last tag, e.g. v4.18.0
# or list the most recent tags:
git tag --sort=-v:refname | head -5
```

Bump rules (SemVer):

- **major** — breaking/backwards-incompatible changes (`v4.x.y` -> `v5.0.0`).
- **minor** — new features, backwards compatible (default; `v4.18.0` -> `v4.19.0`).
- **patch** — bug fixes only (`v4.18.1` -> `v4.18.2`).

The result is the full tag, e.g. `v4.19.0`. Keep the `v` prefix — the
release workflow only triggers on tags matching `v*`.

## 2. Run the promote_changelog script

`scripts/promote_changelog.py` turns the pending `## [Unreleased]` section
into a concrete release entry and opens a fresh, empty `[Unreleased]` on
top. Pass the version determined in step 1:

```bash
uv run python scripts/promote_changelog.py v4.19.0
```

Alternatives:

```bash
# compute the version from the last tag instead of passing it explicitly
uv run python scripts/promote_changelog.py --bump major   # -> v5.0.0
uv run python scripts/promote_changelog.py --bump patch   # -> v4.18.2

# preview the result without writing anything
uv run python scripts/promote_changelog.py v4.19.0 --dry-run
```

The script rewrites:

```markdown
## [Unreleased](https://github.com/joaopinto/janito/compare/v4.18.1...HEAD)
```

into a release heading plus a new empty `[Unreleased]`:

```markdown
## [Unreleased](https://github.com/joaopinto/janito/compare/v4.19.0...HEAD)

## [v4.19.0](https://github.com/joaopinto/janito/compare/v4.18.1...v4.19.0) - 2026-08-05
```

Review `CHANGELOG.md` — make sure the promoted section reads well and the
heading is exactly `## [vX.Y.Z]` (the tag and the heading must match).

## 3. Commit the changelog changes

Stage and commit the changelog. The `changelog-freshness` pre-commit hook
passes because `CHANGELOG.md` is staged:

```bash
git add CHANGELOG.md
git commit -m "chore(release): promote CHANGELOG for v4.19.0"
```

> If the hook complains about `CHANGELOG.md` being stale, it means the file
> was not staged — `git add` it and commit again.

## 4. Tag

Create an **annotated** tag for the version and push it:

```bash
git tag -a v4.19.0 -m "Release version 4.19.0"
git push origin main
git push origin v4.19.0
```

Pushing the tag triggers the release workflow
(`.github/workflows/release.yaml`), which:

1. **Verifies the changelog** — runs `scripts/check_changelog_freshness.py`
   in version mode (`CHANGELOG_REQUIRE_VERSION=v4.19.0`) and fails fast
   unless `CHANGELOG.md` contains the exact `## [v4.19.0]` heading. A bare
   `[Unreleased]` section is not enough.
2. Builds the wheel and sdist.
3. Publishes to PyPI.
4. Creates the GitHub Release with generated release notes.

## Troubleshooting

- **Workflow fails with "has no release entry for vX.Y.Z"** — the tag and the
  changelog heading don't match. Fix `CHANGELOG.md` (or the tag), commit,
  and push again.
- **Emergency hotfix without a changelog entry** — the workflow check can be
  bypassed by re-running it without `CHANGELOG_REQUIRE_VERSION`, but add the
  changelog entry immediately afterwards.
- **Bypassing the local pre-commit hook** (one-off, use sparingly):
  `SKIP=changelog-freshness git commit ...` or `git commit --no-verify`.

## Related

- [README_DEV.md](README_DEV.md) — development guide, version management,
  and the release checklist.
- [.github/workflows/release.yaml](.github/workflows/release.yaml) — release
  automation.
- [scripts/promote_changelog.py](scripts/promote_changelog.py) — changelog
  promotion helper.
- [scripts/check_changelog_freshness.py](scripts/check_changelog_freshness.py) —
  changelog freshness/version guard.
