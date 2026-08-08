"""
Shared helpers for the :class:`FindFiles` tool.

Pure functions extracted from ``janito.tools.files.find_files`` so the tool
class stays focused on orchestration: size parsing, mtime-threshold
computation, per-entry filter predicates and the human-readable start/result
report lines.  The class re-uses these through module-level imports.
"""

import os
import stat as stat_mod
import time

from ...tooling import norm_path
from .glob_utils import matches_any_pattern


def _parse_size(value: int | str | None) -> int | None:
    """
    Parse a human-friendly size value into bytes.

    Accepts plain integers (bytes) or strings with a suffix:
    KB, MB, GB (case-insensitive, powers of 1024).

    Args:
        value: An int (bytes) or a string like "10MB", "512kb", "1GB".

    Returns:
        int or None: Size in bytes, or None if value is None.
    """
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return int(value)

    value = value.strip().upper()
    multipliers = {
        "KB": 1024,
        "MB": 1024**2,
        "GB": 1024**3,
    }
    for suffix, mult in multipliers.items():
        if value.endswith(suffix):
            number = value[: -len(suffix)].strip()
            return int(float(number) * mult)

    return int(value)


def time_thresholds(
    modified_within_days: float | None,
    older_than_days: float | None,
) -> tuple[float | None, float | None]:
    """Compute mtime boundaries from the day-based criteria.

    Args:
        modified_within_days: Only include entries modified within the last
            N days.
        older_than_days: Only include entries modified more than N days ago.

    Returns:
        Tuple of ``(newer_than, older_than)`` epoch timestamps.
    """
    now = time.time()
    newer_than = None
    older_than = None
    if modified_within_days is not None:
        newer_than = now - modified_within_days * 86400
    if older_than_days is not None:
        older_than = now - older_than_days * 86400
    return newer_than, older_than


def matches_type(st: os.stat_result, file_type: str | None) -> bool:
    """Check the file_type filter against a stat result.

    Args:
        st: The ``os.stat``/``os.lstat`` result for the entry.
        file_type: "file", "dir", "symlink", or None (all types).

    Returns:
        True when the entry matches the requested type.
    """
    if file_type is None:
        return True
    is_link = stat_mod.S_ISLNK(st.st_mode)
    if file_type == "symlink":
        return is_link
    if file_type == "dir":
        return stat_mod.S_ISDIR(st.st_mode)
    if file_type == "file":
        return not is_link and stat_mod.S_ISREG(st.st_mode)
    return False


def matches_pattern_and_exclude(
    rel_path: str,
    pattern: str | None,
    exclude_patterns: list[str],
) -> bool:
    """Check pattern and exclude globs against the relative path.

    Args:
        rel_path: The path relative to the search root.
        pattern: Optional include glob (None matches everything).
        exclude_patterns: Space-separated glob patterns to exclude.

    Returns:
        True when the entry passes both the include and exclude filters.
    """
    if pattern is not None and not matches_any_pattern(rel_path, [pattern]):
        return False
    if exclude_patterns and matches_any_pattern(rel_path, exclude_patterns):
        return False
    return True


def matches_size_and_time(
    st: os.stat_result,
    min_bytes: int | None,
    max_bytes: int | None,
    newer_than: float | None,
    older_than: float | None,
) -> bool:
    """Check size and mtime filters against a stat result.

    Args:
        st: The ``os.stat``/``os.lstat`` result for the entry.
        min_bytes: Minimum file size in bytes (None = no lower bound).
        max_bytes: Maximum file size in bytes (None = no upper bound).
        newer_than: Only include entries with mtime >= this epoch.
        older_than: Only include entries with mtime <= this epoch.

    Returns:
        True when the entry passes all size/time filters.
    """
    if min_bytes is not None and st.st_size < min_bytes:
        return False
    if max_bytes is not None and st.st_size > max_bytes:
        return False
    if newer_than is not None and st.st_mtime < newer_than:
        return False
    if older_than is not None and st.st_mtime > older_than:
        return False
    return True


def entry_matches(
    rel_path: str,
    full_path: str,
    st: os.stat_result,
    pattern: str | None,
    exclude_patterns: list[str],
    file_type: str | None,
    min_bytes: int | None,
    max_bytes: int | None,
    newer_than: float | None,
    older_than: float | None,
) -> bool:
    """Return True if a single filesystem entry passes all filters.

    Args:
        rel_path: The path relative to the search root.
        full_path: The absolute path (used for symlink/type checks).
        st: The ``os.stat``/``os.lstat`` result for the entry.
        pattern: Optional include glob.
        exclude_patterns: Glob patterns to exclude.
        file_type: "file", "dir", "symlink", or None.
        min_bytes: Minimum file size in bytes.
        max_bytes: Maximum file size in bytes.
        newer_than: Only include entries with mtime >= this epoch.
        older_than: Only include entries with mtime <= this epoch.

    Returns:
        True when the entry matches every filter.
    """
    if not matches_type(st, file_type):
        return False
    if not matches_pattern_and_exclude(rel_path, pattern, exclude_patterns):
        return False
    if not matches_size_and_time(st, min_bytes, max_bytes, newer_than, older_than):
        return False
    return True


def report_search_start(
    tool,
    valid_paths: list[str],
    pattern: str | None,
    file_type: str | None,
    min_bytes: int | None,
    max_bytes: int | None,
    modified_within_days: float | None,
    older_than_days: float | None,
) -> None:
    """Report the search start with a human-readable criteria summary.

    Args:
        tool: The ``FindFiles`` instance (for ``report_start``).
        valid_paths: The resolved root paths being searched.
        pattern: The include glob (if any).
        file_type: The type filter (if any).
        min_bytes: Minimum file size in bytes (if any).
        max_bytes: Maximum file size in bytes (if any).
        modified_within_days: The "modified within" criterion (if any).
        older_than_days: The "older than" criterion (if any).
    """
    paths_str = ", ".join(norm_path(p) for p in valid_paths[:3])
    if len(valid_paths) > 3:
        paths_str += f" (+{len(valid_paths) - 3} more)"
    criteria: list[str] = []
    if pattern:
        criteria.append(f"pattern='{pattern}'")
    if file_type:
        criteria.append(f"type={file_type}")
    if min_bytes is not None or max_bytes is not None:
        size_desc = []
        if min_bytes is not None:
            size_desc.append(f">={min_bytes}B")
        if max_bytes is not None:
            size_desc.append(f"<={max_bytes}B")
        criteria.append(f"size {','.join(size_desc)}")
    if modified_within_days is not None:
        criteria.append(f"modified <{modified_within_days}d")
    if older_than_days is not None:
        criteria.append(f"older >{older_than_days}d")
    criteria_str = f" [{', '.join(criteria)}]" if criteria else ""
    tool.report_start(f"\U0001f50e Finding files in {paths_str}{criteria_str}", end="")


def report_result(
    tool, files: list[str], stats: dict[str, int], truncated: bool
) -> None:
    """Report the final summary line.

    Args:
        tool: The ``FindFiles`` instance (for ``report_result``).
        files: The final list of matching relative paths.
        stats: The scan statistics dict.
        truncated: True when ``max_results`` cut off results.
    """
    extra = " (truncated)" if truncated else ""
    ignore_msgs = []
    if stats["gitignore_ignored"]:
        ignore_msgs.append(f"{stats['gitignore_ignored']} ignored by .gitignore")
    if stats["janitoignore_ignored"]:
        ignore_msgs.append(f"{stats['janitoignore_ignored']} ignored by .janitoignore")
    ignore_msg = f", {', '.join(ignore_msgs)}" if ignore_msgs else ""
    tool.report_result(
        f"Found {len(files)} matches from {stats['entries_scanned']} entries{extra}{ignore_msg}"
    )
