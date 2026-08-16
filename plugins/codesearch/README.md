# codesearch plugin

A **trigram-based code search** plugin for janito. It builds a per-project
SQLite index of the current working directory once, then answers search
queries against that index instead of scanning files on every call —
making repeated searches fast even on large code bases.

The plugin contributes:

- **`CodeSearch` tool** — queries the pre-built index and returns matching
  **lines** (`path:lineno: content`).
- **`/codesearch` shell command** — maintains the index
  (`/codesearch update` and `/codesearch recreate`).
- **`on_start()` hook** — creates the index automatically when the plugin
  loads (if missing).

---

## Table of Contents

1. [Capabilities](#capabilities)
2. [How it works](#how-it-works)
3. [Installation / Loading](#installation--loading)
4. [Usage](#usage)
5. [Index lifecycle](#index-lifecycle)
6. [What gets indexed](#what-gets-indexed)
7. [Match semantics](#match-semantics)
8. [Plugin structure](#plugin-structure)
9. [Development](#development)

---

## Capabilities

### Fast, indexed search

The first search triggers a one-time index build. Afterwards, every query
runs against the SQLite trigram index, narrowing the candidate files
before a line-by-line scan. There is no repeated full-tree walk on every
call.

### Whole-word matching

Keywords are matched as **whole words**, delimited by non-word characters
(or the start/end of the line). `foo` does **not** match `foobar` or
`foo_bar`. This avoids the false positives of naive substring search.

### AND / OR match modes

- `match="and"` (default) — every keyword must appear on the **same line**.
- `match="or"` — a line matches when **any** keyword appears.

### Line-level results

`Find` returns the matching **lines** — relative path, 1-based line number
and the line content — formatted as `path:lineno: content`, the same
format used by the other janito search tools.

### Incremental index maintenance

The index is updated in place:

- **Added** files are indexed.
- **Deleted** files are dropped.
- **Changed** files (different last-modified time) are re-indexed.

No full rebuild is needed for routine edits.

### Automatic index creation & refresh

- **On plugin load** (`on_start`): if `./.janito/codesearch.db` is missing,
  the index is built automatically.
- **On tool load** (`should_load`): if the recorded last update is missing
  (an index built before last-update tracking) or older than **1 day**
  (the TTL), the index is refreshed in place with an incremental
  `Update()`. The refresh is best-effort — a failure never prevents the
  tool from loading.

### Respects ignore files

Files and directories matched by `.gitignore` or `.janitoignore` are
excluded from the index, so results never surface gitignored files.
`.janitoignore` is **always** respected, matching the other file tools.

### Safe indexing

The indexer skips:

- Hidden files and directories (names starting with `.`).
- Files whose extension is not in the indexable set (see
  [What gets indexed](#what-gets-indexed)).
- Files larger than 10 MB.
- Binary files (detected by a null byte in the first 8 KB).

### Conditional tool loading

The `CodeSearch` tool is **only advertised to the model when
`./.janito/codesearch.db` exists** in the working directory. Loading the
plugin (which creates the index) or running `/codesearch recreate` makes
the tool available.

---

## How it works

The plugin implements the trigram algorithm described by Russ Cox in
[*Regular Expression Matching with a Trigram Index*](https://swtch.com/~rsc/regexp/regexp4.html)
(the technique behind Google Code Search), with SQLite as the storage
backend.

1. **Indexing** — every indexable file is read and decomposed into its
   3-character substrings (**trigrams**). Each trigram is stored in a
   posting list mapping it to the files that contain it.
2. **Querying** — the trigrams of each keyword are extracted and the
   corresponding posting lists are intersected (AND) or unioned (OR) to
   produce a small set of candidate files.
3. **Line scan** — the candidates are scanned line by line with a
   whole-word regex. This line scan is the authoritative match; the index
   only narrows the candidates. Keywords shorter than 3 characters cannot
   be indexed, so they fall back to scanning the full index (still with
   whole-word matching).

The SQLite backend stores three tables — `files`, `trigrams`, and `meta` —
and uses WAL mode with a versioned schema (dropped and rebuilt on schema
changes).

---

## Installation / Loading

The plugin lives in `plugins/codesearch/` and is loaded with the `--plugin`
flag (see `docs/PLUGINS.md`):

```bash
janito --plugin plugins/codesearch
```

When the plugin loads, `on_start()` checks for `.janito/codesearch.db` in
the current working directory and **creates the index automatically** if it
is missing:

```text
codesearch: no index at ./.janito/codesearch.db, building it (this may take some time)...
```

List loaded plugins (and surface any `on_start` errors):

```bash
janito --list-plugins
```

---

## Usage

### As an agent tool

The `CodeSearch` tool searches the pre-built index for lines containing the
given keywords:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `keywords` | `list[str]` | Yes | — | Keywords to search for, matched as whole words |
| `match` | `str` | No | `"and"` | `"and"` (all keywords on the same line) or `"or"` (any keyword) |

The tool returns a dict with `success`, `keywords`, `match`, `matches`
(each formatted as `path:lineno: content`), and `total_matches`.

Example result:

```text
hello.py:5:     print('hello world')
```

### Shell command (`/codesearch`)

In the interactive shell the `/codesearch` command maintains the index:

```text
/codesearch update     # incrementally update (added/deleted/changed files)
/codesearch recreate   # rebuild the index from scratch
/codesearch help       # show usage
```

`recreate` drops the existing index and re-indexes everything (useful
after major changes or to pick up config changes); `update` is the routine
fast-path.

### Direct engine use

The engine can be driven programmatically:

```python
from codesearch import MATCH, CodeSearch

with CodeSearch(str(Path.cwd()), ".janito/codesearch.db") as cs:
    cs.Create()                       # or cs.Update()
    for m in cs.Find(["hello", "world"], MATCH.AND):
        print(m.format())             # hello.py:5:     print('hello world')
    print(cs.stats())                 # file/trigram counts
    print(cs.last_update())           # operation, timestamp, counts
```

### CLI testing harness

The tool module ships a standalone CLI for testing. It searches the
**current working directory's** index, so run it from a project that has
one, with the plugin directory on `PYTHONPATH`:

```bash
cd /path/to/project-with-index
PYTHONPATH=/path/to/janito/plugins python -m codesearch.tools.code_search hello world --match and
PYTHONPATH=/path/to/janito/plugins python -m codesearch.tools.code_search hello world --json
```

---

## Index lifecycle

| Event | Action |
|-------|--------|
| Plugin load, index missing | `on_start()` builds the index (`Create`) |
| Tool load, last update older than 1 day (or missing) | `should_load()` refreshes in place (`Update`) |
| `/codesearch update` | Incremental update (added/deleted/changed files) |
| `/codesearch recreate` | Full rebuild from scratch |

The index location is `./.janito/codesearch.db` — the same per-project
location the old `janito --init-codesearch` flag used.

---

## What gets indexed

The default indexable extensions cover source code, docs, config and data
formats, for example: `.py`, `.js`, `.ts`, `.jsx`, `.tsx`, `.java`, `.c`,
`.h`, `.cpp`, `.go`, `.rs`, `.rb`, `.php`, `.swift`, `.kt`, `.scala`,
`.lua`, `.sh`, `.sql`, `.html`, `.css`, `.json`, `.yaml`, `.toml`, `.md`,
`.rst`, `.txt`, `.csv`, and more (see `DEFAULT_INDEXABLE_EXTENSIONS` in
`plugins/codesearch/code_search.py`).

Files are skipped when they are:

- Hidden (any path component starts with `.`).
- Matched by `.gitignore` / `.janitoignore`.
- Over the maximum file size (10 MB, `DEFAULT_MAX_FILE_SIZE`).
- Binary (null byte in the first 8 KB).
- Not in the indexable extension set.

---

## Match semantics

- **Whole words only** — keywords are matched as whole words, so `foo`
  does not match `foobar` or `foo_bar`.
- **AND** — every keyword must appear on the same line; lines are filtered
  in keyword order.
- **OR** — a line matches when any keyword appears.
- **Short keywords** — keywords under 3 characters cannot use the trigram
  index; they fall back to scanning the whole index (still whole-word).
- **Stale files** — candidate files that no longer exist on disk are
  skipped during the scan.

---

## Plugin structure

```
plugins/codesearch/
    __init__.py            # plugin contract + on_start() index creation
    code_search.py         # CodeSearch engine (Create/Update/Find, filtering)
    index.py               # SQLite inverted trigram index (schema, posting lists)
    trigram.py             # trigram extraction / query construction
    candidates.py          # candidate selection + line scanning (MATCH, CodeSearchMatch)
    tools/code_search.py   # the CodeSearch tool (docs/TOOL.md) + CLI harness
    cmd/codesearch_cmd.py  # /codesearch update | recreate | help
    tests/                 # plugin-local tests (contract, engine, tool)
```

The plugin is also the **reference implementation** for the janito plugin
system — see `docs/PLUGINS.md` for the contract it satisfies.

---

## Development

Run the plugin-local tests:

```bash
python -m pytest plugins/codesearch/tests
```

The test suite covers:

- The plugin contract (`__init__.py` symbols, `on_start()` auto-build,
  `/codesearch` dispatch).
- The engine: create/update, AND/OR matching, whole-word (not substring)
  matching, ignore-file handling, binary/hidden-file skipping.
- The tool: `should_load()` gating, stale-index refresh, and search
  results.

Contributions follow the repo conventions — see `docs/TOOL.md` and
`docs/PLUGINS.md` before changing tools or the plugin contract.
