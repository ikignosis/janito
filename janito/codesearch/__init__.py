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

    # Search for files containing ALL keywords (AND)
    for path in cs.Find(["foo", "bar"], MATCH.AND):
        print(path)

    # Search for files containing ANY keyword (OR)
    for path in cs.Find(["foo", "bar"], MATCH.OR):
        print(path)
"""

from .code_search import MATCH, CodeSearch

__all__ = ["CodeSearch", "MATCH"]
