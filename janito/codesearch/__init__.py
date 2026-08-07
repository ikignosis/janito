"""
janito.codesearch - Trigram-based code search with SQLite backend.

A code search implementation inspired by Google Code Search (Russ Cox's
trigram index algorithm). Uses SQLite as the storage backend for the
inverted trigram index.

Usage:
    from janito.codesearch import CodeSearch, MATCH

    cs = CodeSearch("/path/to/source", "/path/to/index.db")
    cs.Create()           # Build the index from scratch
    cs.Update()           # Incremental update (add/remove/change files)

    # Search for lines containing ALL keywords (AND), whole-word matched
    for m in cs.Find(["foo", "bar"], MATCH.AND):
        print(m.format())  # -> "path:lineno: content"

    # Search for lines containing ANY keyword (OR)
    for m in cs.Find(["foo", "bar"], MATCH.OR):
        print(f"{m.path}:{m.lineno}: {m.content}")
"""

from .code_search import MATCH, CodeSearch, CodeSearchMatch

__all__ = ["CodeSearch", "MATCH", "CodeSearchMatch"]
