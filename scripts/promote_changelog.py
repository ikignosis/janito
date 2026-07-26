#!/usr/bin/env python3
"""Promote the ``[Unreleased]`` section of CHANGELOG.md to a concrete release.

This turns the pending changelog into a tagged release entry and opens a fresh,
empty ``[Unreleased]`` section on top, e.g.::

    ## [Unreleased](.../compare/v4.11.0...HEAD)      ->  ## [Unreleased](.../compare/v4.12.0...HEAD)
                                                            (fresh, empty)
                                                        ## [v4.12.0](.../compare/v4.11.0...v4.12.0) - 2026-07-26
                                                            (previous Unreleased content)

The resulting ``## [vX.Y.Z]`` heading is exactly what the release workflow's
changelog check (``scripts/check_changelog_freshness.py`` in version mode) looks
for, so running this before tagging keeps the release green.

Version selection:
  * pass an explicit version            ``promote_changelog.py v5.0.0``
  * or let it be computed from the last tag with ``--bump`` (default: minor)

Only the Python standard library is used.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CHANGELOG = REPO_ROOT / "CHANGELOG.md"

UNRELEASED_RE = re.compile(
    r"^##\s*\[Unreleased\](?:\((?P<url>[^)]*)\))?\s*$",
    re.IGNORECASE | re.MULTILINE,
)
NEXT_HEADING_RE = re.compile(r"^##\s+", re.MULTILINE)


class PromotionError(Exception):
    """Raised when the changelog cannot be promoted."""


def _git(*args: str) -> str:
    try:
        return subprocess.run(
            ["git", *args],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        raise PromotionError(f"git {' '.join(args)} failed: {exc}") from exc


def _base_url_from_remote() -> str:
    """Best-effort HTTPS base URL from the ``origin`` remote."""
    remote = _git("remote", "get-url", "origin")
    if remote.startswith("git@"):
        # git@github.com:user/repo.git -> https://github.com/user/repo
        path = remote.split(":", 1)[1]
        return "https://" + path.removesuffix(".git")
    return remote.removesuffix(".git")


def _last_tag() -> str:
    return _git("describe", "--tags", "--abbrev=0")


def _split_version(tag: str) -> tuple[str, tuple[int, int, int]]:
    """Return (prefix, (major, minor, patch)) for a tag like ``v4.11.0``."""
    prefix = ""
    body = tag.strip()
    if body[:1] in ("v", "V"):
        prefix, body = body[0].lower(), body[1:]
    parts = body.split(".")
    nums = []
    for part in parts[:3]:
        m = re.match(r"^(\d+)", part)
        nums.append(int(m.group(1)) if m else 0)
    while len(nums) < 3:
        nums.append(0)
    return prefix, (nums[0], nums[1], nums[2])


def _compute_next_version(last_tag: str, bump: str) -> str:
    prefix, (major, minor, patch) = _split_version(last_tag)
    if bump == "major":
        major, minor, patch = major + 1, 0, 0
    elif bump == "minor":
        minor, patch = minor + 1, 0
    elif bump == "patch":
        patch += 1
    else:  # pragma: no cover - argparse restricts choices
        raise PromotionError(f"unknown bump type: {bump}")
    return f"{prefix}{major}.{minor}.{patch}"


def _normalize_version(requested: str, last_tag: str) -> str:
    """Match the leading-prefix convention of the last tag (``v`` or none)."""
    prefix, _ = _split_version(last_tag)
    has_prefix = requested[:1] in ("v", "V")
    if prefix and not has_prefix:
        return "v" + requested
    if not prefix and has_prefix:
        return requested[1:]
    return requested


def promote(
    changelog_path: Path,
    version: str | None,
    bump: str,
    date: str | None,
    dry_run: bool,
) -> str:
    if not changelog_path.exists():
        raise PromotionError(f"{changelog_path} does not exist.")

    text = changelog_path.read_text(encoding="utf-8")
    match = UNRELEASED_RE.search(text)
    if not match:
        raise PromotionError(
            "No '## [Unreleased]' heading found in the changelog; nothing to promote."
        )

    # --- Determine last tag, base URL and new version --------------------
    url = match.group("url") or ""
    compare_match = re.search(r"(?P<base>.*)/compare/(?P<last>.+)\.\.\.HEAD$", url)
    if compare_match:
        base_url = compare_match.group("base")
        last_tag = compare_match.group("last")
    else:
        base_url = _base_url_from_remote()
        last_tag = _last_tag()

    if version:
        new_version = _normalize_version(version, last_tag)
    else:
        new_version = _compute_next_version(last_tag, bump)

    if new_version == last_tag:
        raise PromotionError(f"New version {new_version} equals the last tag.")

    release_date = date or _dt.date.today().isoformat()
    if date:
        try:
            _dt.datetime.strptime(date, "%Y-%m-%d")
        except ValueError as exc:
            raise PromotionError(f"--date must be YYYY-MM-DD: {exc}") from exc

    # --- Rebuild the changelog -------------------------------------------
    start = match.start()
    next_heading = NEXT_HEADING_RE.search(text, match.end())
    next_start = next_heading.start() if next_heading else len(text)

    body = text[match.end() : next_start].strip("\n")
    if not re.search(r"^###\s+", body, re.MULTILINE):
        print(
            f"⚠ Warning: the [Unreleased] section has no '###' subsections; "
            f"promoting an apparently empty release ({new_version}).",
            file=sys.stderr,
        )

    prefix_text = text[:start]
    suffix_text = text[next_start:]

    unreleased_block = (
        f"## [Unreleased]({base_url}/compare/{new_version}...HEAD)\n\n"
        f"Changes since `{new_version}` ({release_date})."
    )
    release_block = (
        f"## [{new_version}]({base_url}/compare/{last_tag}...{new_version}) "
        f"- {release_date}"
    )

    new_text = prefix_text + unreleased_block + "\n\n" + release_block + "\n\n"
    if body:
        new_text += body + "\n\n"
    new_text += suffix_text

    if dry_run:
        print(new_text)
    else:
        changelog_path.write_text(new_text, encoding="utf-8")

    print(
        f"{'[dry-run] ' if dry_run else ''}Promoted [Unreleased] -> "
        f"[{new_version}] ({release_date}); previous tag: {last_tag}.",
        file=sys.stderr,
    )
    return new_version


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "version",
        nargs="?",
        help="explicit release version (e.g. v4.12.0); overrides --bump",
    )
    parser.add_argument(
        "--bump",
        choices=("major", "minor", "patch"),
        default="minor",
        help="how to compute the version from the last tag (default: minor)",
    )
    parser.add_argument(
        "--date",
        help="release date as YYYY-MM-DD (default: today)",
    )
    parser.add_argument(
        "--changelog",
        default=str(DEFAULT_CHANGELOG),
        help=f"path to the changelog (default: {DEFAULT_CHANGELOG})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print the resulting changelog instead of writing it",
    )
    args = parser.parse_args(argv)

    try:
        promote(
            Path(args.changelog),
            version=args.version,
            bump=args.bump,
            date=args.date,
            dry_run=args.dry_run,
        )
    except PromotionError as exc:
        print(f"✗ {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
