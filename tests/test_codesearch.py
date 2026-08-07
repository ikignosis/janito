"""
Tests for the janito.codesearch package.
"""

import os
import shutil
import sqlite3
import tempfile
import time
import unittest
from pathlib import Path

from janito.codesearch import MATCH, CodeSearch


class TestCodeSearch(unittest.TestCase):
    """Test the CodeSearch class."""

    def setUp(self):
        """Create a temporary directory with test files and a temporary DB."""
        self.test_dir = tempfile.mkdtemp(prefix="codesearch_test_")
        self.source_dir = Path(self.test_dir) / "src"
        self.source_dir.mkdir()
        self.db_path = str(Path(self.test_dir) / "index.db")

        # Create test files
        self._create_file("hello.py", "def hello_world():\n    print('hello world')\n")
        self._create_file("foo.py", "def foo():\n    return 'bar'\n")
        self._create_file("bar.py", "def bar():\n    return 'foo'\n")
        self._create_file("baz.py", "x = 1\ny = 2\nz = 3\n")
        self._create_file("README.md", "# Test Project\n\nThis is a test.\n")
        self._create_file("binary.bin", "\x00\x01\x02\x03")  # Should be skipped
        self._create_file(".hidden.py", "secret = 42\n")  # Should be skipped

    def tearDown(self):
        """Remove the temporary directory."""
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def _create_file(self, rel_path: str, content: str) -> Path:
        """Create a file under source_dir with the given content."""
        path = self.source_dir / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def test_create_and_find_and(self):
        """Test creating an index and performing an AND search."""
        cs = CodeSearch(str(self.source_dir), self.db_path)
        cs.Create()

        # "hello" and "world" both appear in hello.py
        results = list(cs.Find(["hello", "world"], MATCH.AND))
        self.assertIn("hello.py", results)
        self.assertNotIn("foo.py", results)
        cs.close()

    def test_create_and_find_or(self):
        """Test creating an index and performing an OR search."""
        cs = CodeSearch(str(self.source_dir), self.db_path)
        cs.Create()

        # "foo" or "bar" should match foo.py and bar.py
        results = list(cs.Find(["foo", "bar"], MATCH.OR))
        self.assertIn("foo.py", results)
        self.assertIn("bar.py", results)
        cs.close()

    def test_find_no_results(self):
        """Test a search that matches nothing."""
        cs = CodeSearch(str(self.source_dir), self.db_path)
        cs.Create()

        results = list(cs.Find(["nonexistent", "keyword"], MATCH.AND))
        self.assertEqual(results, [])
        cs.close()

    def test_update_added_file(self):
        """Test that Update indexes newly added files."""
        cs = CodeSearch(str(self.source_dir), self.db_path)
        cs.Create()

        # Add a new file
        self._create_file("new_file.py", "def new_function():\n    pass\n")

        cs.Update()
        results = list(cs.Find(["new_function"], MATCH.AND))
        self.assertIn("new_file.py", results)
        cs.close()

    def test_update_deleted_file(self):
        """Test that Update removes deleted files from the index."""
        cs = CodeSearch(str(self.source_dir), self.db_path)
        cs.Create()

        # Delete a file
        os.remove(self.source_dir / "baz.py")

        cs.Update()
        results = list(cs.Find(["x = 1"], MATCH.AND))
        self.assertNotIn("baz.py", results)
        cs.close()

    def test_update_changed_file(self):
        """Test that Update re-indexes changed files (detected by mtime)."""
        cs = CodeSearch(str(self.source_dir), self.db_path)
        cs.Create()

        # Change a file and bump its mtime so the change is detected
        # regardless of filesystem timestamp granularity.
        changed = self._create_file("foo.py", "def foo():\n    return 'changed'\n")
        os.utime(changed, (time.time() + 10, time.time() + 10))

        cs.Update()
        results = list(cs.Find(["changed"], MATCH.AND))
        self.assertIn("foo.py", results)

        # Old content should no longer match
        results = list(cs.Find(["bar"], MATCH.AND))
        self.assertNotIn("foo.py", results)
        cs.close()

    def test_update_ignores_unchanged_file(self):
        """Update() leaves files alone when their mtime did not change."""
        cs = CodeSearch(str(self.source_dir), self.db_path)
        cs.Create()

        from janito.codesearch.index import Index

        # Record the mtime that was indexed for baz.py, then rewrite the
        # file while keeping that same mtime.
        indexed_mtime = Index(self.db_path).get_file("baz.py")["mtime"]
        untouched = self.source_dir / "baz.py"
        untouched.write_text("changed = True\n", encoding="utf-8")
        os.utime(untouched, (indexed_mtime, indexed_mtime))

        cs.Update()

        # The file is not re-indexed (its mtime still matches), so the new
        # content is not searchable.
        results = list(cs.Find(["changed"], MATCH.AND))
        self.assertNotIn("baz.py", results)
        cs.close()

    def test_files_table_has_no_sha1_column(self):
        """The index tracks files by mtime, not by a content hash."""
        cs = CodeSearch(str(self.source_dir), self.db_path)
        cs.Create()

        conn = sqlite3.connect(self.db_path)
        cols = [r[1] for r in conn.execute("PRAGMA table_info(files)")]
        conn.close()
        self.assertNotIn("sha1", cols)

        from janito.codesearch.index import Index

        index = Index(self.db_path)
        file_info = index.get_file("hello.py")
        self.assertIsNotNone(file_info)
        self.assertIn("mtime", file_info)
        self.assertNotIn("sha1", file_info)
        index.close()
        cs.close()

    def test_update_migrates_old_schema(self):
        """Update() rebuilds an index created with the old sha1 schema."""
        # Simulate an index produced by the previous schema version (v1),
        # which stored a per-file SHA-1 content hash.
        conn = sqlite3.connect(self.db_path)
        conn.executescript(
            """
            CREATE TABLE meta (
                key   TEXT PRIMARY KEY,
                value TEXT
            );
            CREATE TABLE files (
                id      INTEGER PRIMARY KEY AUTOINCREMENT,
                path    TEXT UNIQUE NOT NULL,
                sha1    TEXT NOT NULL,
                mtime   REAL NOT NULL,
                size    INTEGER NOT NULL
            );
            CREATE TABLE trigrams (
                trigram TEXT NOT NULL,
                file_id INTEGER NOT NULL,
                PRIMARY KEY (trigram, file_id)
            );
            INSERT INTO meta(key, value) VALUES ('schema_version', '1');
            INSERT INTO files(path, sha1, mtime, size)
                VALUES ('hello.py', 'abc', 1.0, 10);
            """
        )
        conn.commit()
        conn.close()

        cs = CodeSearch(str(self.source_dir), self.db_path)
        cs.Update()  # detects the old schema and rebuilds in place

        conn = sqlite3.connect(self.db_path)
        cols = [r[1] for r in conn.execute("PRAGMA table_info(files)")]
        conn.close()
        self.assertNotIn("sha1", cols)

        # The index was rebuilt from disk and is searchable again
        results = list(cs.Find(["hello"], MATCH.AND))
        self.assertIn("hello.py", results)
        cs.close()

    def test_binary_and_hidden_files_skipped(self):
        """Test that binary and hidden files are not indexed."""
        cs = CodeSearch(str(self.source_dir), self.db_path)
        cs.Create()

        stats = cs.stats()
        # binary.bin and .hidden.py should be skipped
        self.assertEqual(stats["file_count"], 5)
        cs.close()

    def test_gitignored_files_skipped(self):
        """Files and directories matched by .gitignore are not indexed."""
        self._create_file(".gitignore", "secret.py\nignored_dir/\n")
        self._create_file("secret.py", "def top_secret():\n    pass\n")
        self._create_file("ignored_dir/gen.py", "def generated():\n    pass\n")

        cs = CodeSearch(str(self.source_dir), self.db_path)
        cs.Create()

        # hello.py, foo.py, bar.py, baz.py, README.md (secret.py and
        # ignored_dir/ are gitignored; .gitignore itself is hidden)
        self.assertEqual(cs.stats()["file_count"], 5)

        self.assertNotIn("secret.py", list(cs.Find(["top_secret"], MATCH.AND)))
        self.assertNotIn("ignored_dir/gen.py", list(cs.Find(["generated"], MATCH.AND)))
        self.assertIn("hello.py", list(cs.Find(["hello"], MATCH.AND)))
        cs.close()

    def test_update_removes_newly_gitignored_file(self):
        """Update() drops files that were added to .gitignore since Create()."""
        cs = CodeSearch(str(self.source_dir), self.db_path)
        cs.Create()

        self.assertIn("hello.py", list(cs.Find(["hello"], MATCH.AND)))

        # Ignore hello.py and re-sync
        self._create_file(".gitignore", "hello.py\n")
        cs.Update()

        self.assertNotIn("hello.py", list(cs.Find(["hello"], MATCH.AND)))
        self.assertEqual(cs.stats()["file_count"], 4)
        cs.close()

    def test_janitoignore_files_skipped(self):
        """.janitoignore is always respected by the indexer."""
        self._create_file(".janitoignore", "secret.py\n")
        self._create_file("secret.py", "def top_secret():\n    pass\n")

        cs = CodeSearch(str(self.source_dir), self.db_path)
        cs.Create()

        self.assertEqual(cs.stats()["file_count"], 5)
        self.assertNotIn("secret.py", list(cs.Find(["top_secret"], MATCH.AND)))
        cs.close()

    def test_short_keyword_and(self):
        """Test that short keywords (< 3 chars) in AND mode match all files."""
        cs = CodeSearch(str(self.source_dir), self.db_path)
        cs.Create()

        results = list(cs.Find(["ab"], MATCH.AND))
        # Should return all indexed files
        self.assertEqual(len(results), 5)
        cs.close()

    def test_short_keyword_or(self):
        """Test that short keywords (< 3 chars) in OR mode match all files."""
        cs = CodeSearch(str(self.source_dir), self.db_path)
        cs.Create()

        results = list(cs.Find(["ab"], MATCH.OR))
        # Should return all indexed files
        self.assertEqual(len(results), 5)
        cs.close()

    def test_empty_keywords(self):
        """Test that an empty keyword list returns no results."""
        cs = CodeSearch(str(self.source_dir), self.db_path)
        cs.Create()

        results = list(cs.Find([], MATCH.AND))
        self.assertEqual(results, [])
        cs.close()

    def test_context_manager(self):
        """Test using CodeSearch as a context manager."""
        with CodeSearch(str(self.source_dir), self.db_path) as cs:
            cs.Create()
            results = list(cs.Find(["hello"], MATCH.AND))
            self.assertIn("hello.py", results)

    def test_stats(self):
        """Test the stats method."""
        cs = CodeSearch(str(self.source_dir), self.db_path)
        cs.Create()

        stats = cs.stats()
        self.assertEqual(stats["file_count"], 5)
        self.assertGreater(stats["trigram_count"], 0)
        self.assertEqual(stats["source_path"], str(self.source_dir.resolve()))
        self.assertEqual(stats["index_db_path"], self.db_path)
        cs.close()

    def test_create_twice(self):
        """Test that Create can be called twice (rebuilds from scratch)."""
        cs = CodeSearch(str(self.source_dir), self.db_path)
        cs.Create()
        stats1 = cs.stats()

        # Add a file and re-create
        self._create_file("extra.py", "def extra():\n    pass\n")
        cs.Create()
        stats2 = cs.stats()

        self.assertEqual(stats2["file_count"], stats1["file_count"] + 1)
        cs.close()

    def test_update_no_changes(self):
        """Test that Update with no changes is a no-op."""
        cs = CodeSearch(str(self.source_dir), self.db_path)
        cs.Create()
        stats1 = cs.stats()

        cs.Update()
        stats2 = cs.stats()

        self.assertEqual(stats1["file_count"], stats2["file_count"])
        self.assertEqual(stats1["trigram_count"], stats2["trigram_count"])
        cs.close()

    def test_last_update_none_before_create(self):
        """Test that last_update() is None before any Create/Update."""
        cs = CodeSearch(str(self.source_dir), self.db_path)
        self.assertIsNone(cs.last_update())
        cs.close()

    def test_last_update_after_create(self):
        """Test that Create() records last-update info in the DB."""
        cs = CodeSearch(str(self.source_dir), self.db_path)
        cs.Create()

        info = cs.last_update()
        self.assertIsNotNone(info)
        self.assertEqual(info["operation"], "create")
        self.assertIn("timestamp", info)
        self.assertIn("timestamp_epoch", info)
        self.assertEqual(info["file_count"], 5)
        self.assertGreater(info["trigram_count"], 0)
        cs.close()

    def test_last_update_after_update(self):
        """Test that Update() refreshes the last-update info in the DB."""
        cs = CodeSearch(str(self.source_dir), self.db_path)
        cs.Create()

        self._create_file("new_file.py", "def new_function():\n    pass\n")
        cs.Update()

        info = cs.last_update()
        self.assertIsNotNone(info)
        self.assertEqual(info["operation"], "update")
        self.assertEqual(info["file_count"], 6)
        cs.close()

    def test_last_update_persists_across_instances(self):
        """Test that last-update info survives closing/reopening the DB."""
        cs = CodeSearch(str(self.source_dir), self.db_path)
        cs.Create()
        cs.close()

        cs2 = CodeSearch(str(self.source_dir), self.db_path)
        info = cs2.last_update()
        self.assertIsNotNone(info)
        self.assertEqual(info["operation"], "create")
        self.assertEqual(info["file_count"], 5)
        cs2.close()

    def test_last_modified_none_before_create(self):
        """Test that last_modified() is None before any Create/Update."""
        cs = CodeSearch(str(self.source_dir), self.db_path)
        self.assertIsNone(cs.last_modified())
        cs.close()

    def test_last_modified_after_create(self):
        """Test that last_modified() returns the epoch of the last update."""
        cs = CodeSearch(str(self.source_dir), self.db_path)
        cs.Create()

        last_modified = cs.last_modified()
        self.assertIsNotNone(last_modified)
        self.assertAlmostEqual(last_modified, time.time(), delta=60)
        cs.close()

    def test_last_modified_refreshed_by_update(self):
        """Test that Update() moves last_modified() forward in time."""
        cs = CodeSearch(str(self.source_dir), self.db_path)
        cs.Create()
        before = cs.last_modified()

        time.sleep(0.01)
        self._create_file("new_file.py", "def new_function():\n    pass\n")
        cs.Update()

        after = cs.last_modified()
        self.assertIsNotNone(after)
        self.assertGreaterEqual(after, before)
        cs.close()


class TestTrigramExtraction(unittest.TestCase):
    """Test trigram extraction utilities."""

    def test_extract_trigrams(self):
        from janito.codesearch.trigram import extract_trigrams

        self.assertEqual(extract_trigrams("abcd"), {"abc", "bcd"})
        self.assertEqual(extract_trigrams("abc"), {"abc"})
        self.assertEqual(extract_trigrams("ab"), set())
        self.assertEqual(extract_trigrams(""), set())

    def test_trigrams_for_keyword(self):
        from janito.codesearch.trigram import trigrams_for_keyword

        self.assertEqual(trigrams_for_keyword("hello"), {"hel", "ell", "llo"})
        self.assertEqual(trigrams_for_keyword("hi"), set())

    def test_build_trigram_query(self):
        from janito.codesearch.trigram import build_trigram_query

        result = build_trigram_query(["hello", "hi", "world"])
        self.assertEqual(result["hello"], {"hel", "ell", "llo"})
        self.assertEqual(result["hi"], set())
        self.assertEqual(result["world"], {"wor", "orl", "rld"})


if __name__ == "__main__":
    unittest.main()
