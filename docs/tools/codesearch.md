# Code Search

The `CodeSearch` tool searches a **pre-built trigram index** of the current
working directory instead of scanning files on every call. It is provided by
the **codesearch plugin** (`../plugins/janito-codesearch-plugin/`),
not the core package.

The index is stored at `./.janito/codesearch.db` and is built automatically
when the plugin loads. Load the plugin and use it:

```bash
janito --plugin ../plugins/janito-codesearch-plugin
```

!!! note "Automatic index creation"

    When the codesearch plugin loads (`on_start`), if there is no
    `./.janito/codesearch.db` in the current working directory, the index is
    created automatically. No separate build step is needed.

!!! note "Maintaining the index"

    In the interactive shell the `/codesearch` command maintains the index:

    - `/codesearch update` — incrementally update (added/deleted/changed files)
    - `/codesearch recreate` — rebuild the index from scratch

!!! note "Conditional loading"

    The `CodeSearch` tool is **only loaded when `./.janito/codesearch.db`
    exists** in the working directory. If you haven't built the index yet,
    the tool is not advertised to the model — load the codesearch plugin
    (creates it automatically) or run `/codesearch recreate`.

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
    of the other file tools, and the `.janitoignore` file itself is always
    ignored. When a file becomes gitignored after the
    index was built, the next `Update()` drops it from the index.

## CodeSearch

Searches the trigram index for **lines** containing the given keywords.
Keywords are matched as **whole words** (`foo` does not match `foobar` or
`foo_bar`). The index narrows the candidate files, and every matching line
is returned as `path:lineno: content` — the same format used by the other
search tools.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `keywords` | `array` of `string` | Yes | Keywords to search for, matched as whole words. Keywords shorter than 3 characters cannot be indexed and are matched by scanning candidate files directly |
| `match` | `string` | No | `"and"` (every keyword must appear on the same line) or `"or"` (any keyword is sufficient). Defaults to `"and"` |

Example:

```python
result = CodeSearch(keywords=["hello", "world"], match="and")
# result["matches"] == ["hello.py:5:     print('hello world')"]
```

For `"and"`, lines are filtered in keyword order: lines containing the
first keyword are found first, then narrowed to those also containing the
second, third, ... keyword. Files that are in the index but no longer
exist on disk are skipped.

The index uses the trigram algorithm described by Russ Cox in *Regular
Expression Matching with a Trigram Index* (Google Code Search), with SQLite
as the storage backend. See `../plugins/janito-codesearch-plugin/`
for the implementation.
