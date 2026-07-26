#!/usr/bin/env python3
"""Pre-commit / CI check: ensure CHANGELOG.md is up to date.

Two modes:

* **Version mode (CI / release):** if ``CHANGELOG_REQUIRE_VERSION`` is set
  (e.g. ``v4.12.0``), the hook passes only if ``CHANGELOG.md`` contains an
  entry for that version. This guarantees the changelog was updated for the
  release rather than left as ``[Unreleased]``. mtime is meaningless in CI
  because ``actions/checkout`` resets file timestamps.

* **Freshness mode (local pre-commit):** otherwise the hook passes if *either*
  ``CHANGELOG.md`` is staged in the current commit (updated right now) or its
  modification time is newer than the allowed age. The allowed age (seconds) is
  tunable via ``CHANGELOG_MAX_AGE_SECONDS`` (default: 3600 = 1 hour).

Exit codes: 0 = ok, 1 = changelog is stale / missing / lacks the version.
"""

from __future__ import annotations

import os
import subprocess
import time

CHANGELOG = "CHANGELOG.md"
DEFAULT_MAX_AGE_SECONDS = 3600  # 1 hour


def _human(seconds: float) -> str:
    seconds = int(seconds)
    if seconds < 60:
        return f"{seconds}s"
    if seconds < 3600:
        return f"{seconds // 60}m"
    return f"{seconds // 3600}h{(seconds % 3600) // 60:02d}m"


def _is_staged() -> bool:
    """True if CHANGELOG.md is part of the staged changes for this commit."""
    try:
        out = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "-z"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False
    staged = {name for name in out.split("\0") if name}
    return CHANGELOG in staged


def _has_version_entry(version: str) -> bool:
    """True if CHANGELOG.md references ``version`` in a release heading.

    Matches headings such as ``## [v4.12.0]``, ``## [4.12.0]``, ``## v4.12.0``
    and ``## 4.12.0``. A bare ``[Unreleased]`` section does not count.
    """
    v = version.strip().lstrip("vV")
    if not v:
        return False
    with open(CHANGELOG, encoding="utf-8") as fh:
        text = fh.read()
    # Look for the version as a release heading: "## [vX.Y.Z]" or "## vX.Y.Z".
    patterns = [
        f"## [v{v}]",
        f"## [{v}]",
        f"## v{v}",
        f"## {v}",
    ]
    lowered = text.lower()
    return any(p.lower() in lowered for p in patterns)


def main() -> int:
    if not os.path.exists(CHANGELOG):
        print(f"✗ {CHANGELOG} does not exist. Create/update it before committing.")
        return 1

    # --- Version mode (CI / release) -------------------------------------
    required_version = os.environ.get("CHANGELOG_REQUIRE_VERSION", "").strip()
    if required_version:
        if _has_version_entry(required_version):
            print(f"✓ {CHANGELOG} contains a release entry for {required_version}.")
            return 0
        print(
            f"✗ {CHANGELOG} has no release entry for {required_version}.\n"
            f"  Add a `## [{required_version}]` section (replace `[Unreleased]`) "
            f"documenting this release before tagging.\n"
            f"  To bypass temporarily, re-run without CHANGELOG_REQUIRE_VERSION set."
        )
        return 1

    # --- Freshness mode (local pre-commit) -------------------------------
    try:
        max_age = float(
            os.environ.get("CHANGELOG_MAX_AGE_SECONDS", DEFAULT_MAX_AGE_SECONDS)
        )
    except ValueError:
        max_age = float(DEFAULT_MAX_AGE_SECONDS)

    if _is_staged():
        print(f"✓ {CHANGELOG} is staged for this commit.")
        return 0

    age = time.time() - os.path.getmtime(CHANGELOG)
    if age <= max_age:
        print(
            f"✓ {CHANGELOG} was modified {_human(age)} ago (limit: {_human(max_age)})."
        )
        return 0

    print(
        f"✗ {CHANGELOG} was last modified {_human(age)} ago, "
        f"which is older than the {_human(max_age)} limit.\n"
        f"  Update the changelog (or `touch {CHANGELOG}`) before committing.\n"
        f"  To bypass temporarily: CHANGELOG_MAX_AGE_SECONDS=999999 git commit ... "
        f"or SKIP=changelog-freshness git commit ..."
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
