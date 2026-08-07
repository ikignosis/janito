# Code Search Tools

The `CodeSearch` tool searches a **pre-built trigram index** of the current
working directory instead of scanning files on every call. The index is
stored at `./.janito/codesearch.db` and is built with:

```bash
janito --init-codesearch
```

!!! note "Conditional loading"

    The `CodeSearch` tool is **only loaded when `./.janito/codesearch.db`
    exists** in the working directory. If you haven't built the index yet,
    the tool is not advertised to the model — build it with
    `janito --init-codesearch` first.

!!! note "Automatic refresh (1 day TTL)"

    When the tool loads, the index is refreshed in place with an
    incremental `Update()` if its last recorded update is **missing** (an
    index built before last-update tracking) or **older than 1 day**.
    The refresh is best-effort: a failure never prevents the tool from
    loading — it stays usable with the existing index.

!!! note "Skips gitignored files"

    Files and directories matched by the working directory's `.gitignore`
    are excluded from the index, so search results never surface
    gitignored files (build artifacts, vendored dependencies, secrets,
    ...). `.janitoignore` is **always** respected, matching the behaviour
    of the other file tools. When a file becomes gitignored after the
    index was built, the next `Update()` drops it from the index.

## CodeSearch

Searches the trigram index for files containing the given keywords. Returns
the matching file paths relative to the working directory.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `keywords` | `array` of `string` | Yes | Keywords to search for. Keywords shorter than 3 characters cannot be indexed and match every file |
| `match` | `string` | No | `"and"` (all keywords must be present) or `"or"` (any keyword is sufficient). Defaults to `"and"` |

Example:

```python
result = CodeSearch(keywords=["hello", "world"], match="and")
# result["results"] == ["hello.py"]
```

The index uses the trigram algorithm described by Russ Cox in *Regular
Expression Matching with a Trigram Index* (Google Code Search), with SQLite
as the storage backend. See `janito/codesearch/` for the implementation.
