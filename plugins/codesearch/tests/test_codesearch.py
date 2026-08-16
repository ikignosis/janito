"""Tests for the codesearch plugin engine (plugins/codesearch/code_search)."""

import os
import shutil
import sys
import tempfile
import time
import unittest
from pathlib import Path

# Make ``codesearch`` (the plugin package) importable from plugins/.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from codesearch import MATCH, CodeSearch, CodeSearchMatch


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

        # "hello" and "world" both appear on line 2 of hello.py
        results = list(cs.Find(["hello", "world"], MATCH.AND))
        self.assertEqual(
            [(m.path, m.lineno, m.content) for m in results],
            [("hello.py", 2, "    print('hello world')")],
        )
        cs.close()

    def test_create_and_find_or(self):
        """Test creating an index and performing an OR search."""
        cs = CodeSearch(str(self.source_dir), self.db_path)
        cs.Create()

        # "foo" or "bar" should match lines in foo.py and bar.py
        results = list(cs.Find(["foo", "bar"], MATCH.OR))
        paths = [m.path for m in results]
        self.assertIn("foo.py", paths)
        self.assertIn("bar.py", paths)
        cs.close()

    def test_word_match_not_substring(self):
        """Keywords must match whole words, not substrings."""
        self._create_file(
            "sub.py",
            "foobar = 1\nfoo = 2\nfoo_bar = 3\n",
        )
        cs = CodeSearch(str(self.source_dir), self.db_path)
        cs.Create()

        # "foo" must not match "foobar" or "foo_bar" (it does match foo.py)
        results = list(cs.Find(["foo"], MATCH.AND))
        matches = [(m.path, m.lineno) for m in results]
        self.assertIn(("sub.py", 2), matches)
        self.assertNotIn(("sub.py", 1), matches)
        self.assertNotIn(("sub.py", 3), matches)
        cs.close()

    def test_and_line_match(self):
        """AND matches only lines containing all keywords."""
        self._create_file(
            "multi.py",
            "import os\nimport sys\nimport os\n",
        )
        cs = CodeSearch(str(self.source_dir), self.db_path)
        cs.Create()

        # "import" and "os" co-occur only on lines 1 and 3
        results = list(cs.Find(["import", "os"], MATCH.AND))
        self.assertEqual(
            [(m.path, m.lineno) for m in results],
            [("multi.py", 1), ("multi.py", 3)],
        )
        cs.close()

    def test_match_format(self):
        """CodeSearchMatch.format() renders 'path:lineno: content'."""
        m = CodeSearchMatch(path="a.py", lineno=3, content="x = 1")
        self.assertEqual(m.format(), "a.py:3: x = 1")

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

        self._create_file("new_file.py", "def new_function():\n    pass\n")
        cs.Update()
        results = list(cs.Find(["new_function"], MATCH.AND))
        self.assertIn("new_file.py", [m.path for m in results])
        cs.close()

    def test_update_deleted_file(self):
        """Test that Update removes deleted files from the index."""
        cs = CodeSearch(str(self.source_dir), self.db_path)
        cs.Create()

        os.remove(self.source_dir / "baz.py")
        cs.Update()
        results = list(cs.Find(["x = 1"], MATCH.AND))
        self.assertNotIn("baz.py", [m.path for m in results])
        cs.close()

    def test_update_changed_file(self):
        """Test that Update re-indexes changed files (detected by mtime)."""
        cs = CodeSearch(str(self.source_dir), self.db_path)
        cs.Create()

        changed = self._create_file("foo.py", "def foo():\n    return 'changed'\n")
        os.utime(changed, (time.time() + 10, time.time() + 10))

        cs.Update()
        results = list(cs.Find(["changed"], MATCH.AND))
        self.assertIn("foo.py", [m.path for m in results])
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

        self.assertEqual(cs.stats()["file_count"], 5)
        self.assertNotIn(
            "secret.py", [m.path for m in cs.Find(["top_secret"], MATCH.AND)]
        )
        self.assertNotIn(
            "ignored_dir/gen.py",
            [m.path for m in cs.Find(["generated"], MATCH.AND)],
        )
        cs.close()

    def test_short_keyword_and(self):
        """Short keywords (< 3 chars) are still word-matched on lines."""
        cs = CodeSearch(str(self.source_dir), self.db_path)
        cs.Create()

        results = list(cs.Find(["x"], MATCH.AND))
        self.assertEqual(
            [(m.path, m.lineno, m.content) for m in results],
            [("baz.py", 1, "x = 1")],
        )
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
            self.assertIn("hello.py", [m.path for m in results])

    def test_stats(self):
        """Test the stats method."""
        cs = CodeSearch(str(self.source_dir), self.db_path)
        cs.Create()

        stats = cs.stats()
        self.assertEqual(stats["file_count"], 5)
        self.assertGreater(stats["trigram_count"], 0)
        cs.close()

    def test_last_update_after_create(self):
        """Test that Create() records last-update info in the DB."""
        cs = CodeSearch(str(self.source_dir), self.db_path)
        cs.Create()

        info = cs.last_update()
        self.assertIsNotNone(info)
        self.assertEqual(info["operation"], "create")
        self.assertEqual(info["file_count"], 5)
        cs.close()

    def test_last_modified_after_create(self):
        """Test that last_modified() returns the epoch of the last update."""
        cs = CodeSearch(str(self.source_dir), self.db_path)
        cs.Create()

        last_modified = cs.last_modified()
        self.assertIsNotNone(last_modified)
        self.assertAlmostEqual(last_modified, time.time(), delta=60)
        cs.close()


class TestTrigramExtraction(unittest.TestCase):
    """Test trigram extraction utilities."""

    def test_extract_trigrams(self):
        from codesearch.trigram import extract_trigrams

        self.assertEqual(extract_trigrams("abcd"), {"abc", "bcd"})
        self.assertEqual(extract_trigrams("abc"), {"abc"})
        self.assertEqual(extract_trigrams("ab"), set())
        self.assertEqual(extract_trigrams(""), set())

    def test_trigrams_for_keyword(self):
        from codesearch.trigram import trigrams_for_keyword

        self.assertEqual(trigrams_for_keyword("hello"), {"hel", "ell", "llo"})
        self.assertEqual(trigrams_for_keyword("hi"), set())

    def test_build_trigram_query(self):
        from codesearch.trigram import build_trigram_query

        result = build_trigram_query(["hello", "hi", "world"])
        self.assertEqual(result["hello"], {"hel", "ell", "llo"})
        self.assertEqual(result["hi"], set())
        self.assertEqual(result["world"], {"wor", "orl", "rld"})


if __name__ == "__main__":
    unittest.main()
