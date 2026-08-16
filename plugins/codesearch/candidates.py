"""
Candidate selection and line scanning for trigram code search.

The :class:`~codesearch.code_search.CodeSearch` class narrows the
candidate files with the trigram index and then scans those candidates line
by line for whole-word matches.  These helpers were extracted from
``codesearch.code_search`` so the class stays focused on index
lifecycle (create/update/close) while the matching logic lives here.
"""

import re
from collections.abc import Iterator
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path

from .trigram import build_trigram_query


class MATCH(Enum):
    """Match mode for keyword search."""

    AND = auto()  # All keywords must be present
    OR = auto()  # Any keyword may be present


@dataclass(frozen=True)
class CodeSearchMatch:
    """
    A single matching line produced by ``CodeSearch.Find``.

    Attributes:
        path: Relative file path (POSIX style), relative to the source
            root that was indexed.
        lineno: 1-based line number of the match.
        content: The full line content without the trailing newline.
    """

    path: str
    lineno: int
    content: str

    def format(self) -> str:
        """
        Render the match in the same format as the other search tools.

        Returns:
            A string ``"path:lineno: content"`` (e.g. ``src/main.py:42: x``).
        """
        return f"{self.path}:{self.lineno}: {self.content}"


def compile_matchers(keywords: list[str]):
    """Compile whole-word matchers and split keywords by trigram support."""
    compiled = [
        (kw, re.compile(r"(?<!\w)" + re.escape(kw) + r"(?!\w)")) for kw in keywords
    ]
    keyword_trigrams = build_trigram_query(keywords)
    keywords_with_trigrams = {kw: tgs for kw, tgs in keyword_trigrams.items() if tgs}
    keywords_without_trigrams = {kw for kw, tgs in keyword_trigrams.items() if not tgs}
    return compiled, keywords_with_trigrams, keywords_without_trigrams


def and_candidates(index, keywords_with_trigrams) -> list[int] | None:
    """Intersect the trigram posting lists for MATCH.AND."""
    all_trigrams: set[str] = set()
    for tgs in keywords_with_trigrams.values():
        all_trigrams.update(tgs)

    if not all_trigrams:
        return None

    candidate_ids: set[int] | None = None
    for trigram in all_trigrams:
        posting = set(index.get_posting_list(trigram))
        if candidate_ids is None:
            candidate_ids = posting
        else:
            candidate_ids &= posting
        # Early exit if no candidates left
        if not candidate_ids:
            return None

    return sorted(candidate_ids)


def or_candidates(index, keywords_with_trigrams) -> list[int] | None:
    """Union the trigram posting lists for MATCH.OR."""
    candidate_ids = set()
    for tgs in keywords_with_trigrams.values():
        keyword_ids: set[int] | None = None
        for trigram in tgs:
            posting = set(index.get_posting_list(trigram))
            if keyword_ids is None:
                keyword_ids = posting
            else:
                keyword_ids &= posting
        if keyword_ids:
            candidate_ids.update(keyword_ids)

    if not candidate_ids:
        return None

    return sorted(candidate_ids)


def candidate_paths(
    index,
    keywords: list[str],
    match: MATCH,
    keywords_with_trigrams,
    keywords_without_trigrams,
) -> list[str]:
    """Return the candidate file paths to scan, narrowed by the index.

    A short keyword (fewer than 3 characters) has no trigrams, so the
    index cannot narrow the search for it and every indexed file is a
    candidate.
    """
    if match == MATCH.OR and keywords_without_trigrams:
        return [f["path"] for f in index.get_all_files()]
    if match == MATCH.AND and not keywords_with_trigrams:
        return [f["path"] for f in index.get_all_files()]

    if match == MATCH.AND:
        file_ids = and_candidates(index, keywords_with_trigrams)
    else:  # MATCH.OR
        file_ids = or_candidates(index, keywords_with_trigrams)

    if file_ids is None:
        return []

    # Resolve file IDs to candidate paths
    path_map = index.get_file_paths(file_ids)
    return [path_map[fid] for fid in file_ids if path_map.get(fid) is not None]


def scan_candidates(
    source_path, candidates, match: MATCH, compiled
) -> Iterator[CodeSearchMatch]:
    """Scan candidate files line by line; yield whole-word matches.

    This line scan is the authoritative word match.
    """
    for rel_path in candidates:
        filepath = Path(source_path) / rel_path
        if not filepath.is_file():
            # Indexed file no longer exists on disk -> skip it.
            continue
        try:
            with open(filepath, encoding="utf-8", errors="ignore") as fh:
                for lineno, line in enumerate(fh, 1):
                    content = line.rstrip("\n")
                    if match == MATCH.AND:
                        matched = all(regex.search(content) for _, regex in compiled)
                    else:
                        matched = any(regex.search(content) for _, regex in compiled)
                    if matched:
                        yield CodeSearchMatch(
                            path=rel_path, lineno=lineno, content=content
                        )
        except OSError:
            # Skip files that cannot be read (permissions, binary, ...)
            continue
