"""
Code Search Tools - Tools for searching the trigram code search index.

This toolset provides the ``CodeSearch`` tool, which queries the per-project
SQLite index stored at ``./.janito/codesearch.db`` (built with
``janito --init-codesearch``). The tool is only loaded when that index
database is present in the current working directory.

Note: Tools in this package are automatically discovered via the @tool decorator
and do not need to be explicitly imported in this __init__.py file.
"""
