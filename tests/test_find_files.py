import os
import shutil
import tempfile
from janito.agent.tools.find_files import FindFilesTool


def setup_test_dir():
    base = tempfile.mkdtemp()
    os.makedirs(os.path.join(base, "dirA"))
    os.makedirs(os.path.join(base, "dirB"))
    with open(os.path.join(base, "file1.txt"), "w") as f:
        f.write("abc")
    with open(os.path.join(base, "dirA", "file2.txt"), "w") as f:
        f.write("def")
    with open(os.path.join(base, "dirB", "file2.txt"), "w") as f:
        f.write("ghi")
    return base


def teardown_test_dir(base):
    shutil.rmtree(base)


def test_find_files_returns_files_and_dirs():
    base = setup_test_dir()
    try:
        tool = FindFilesTool()
        # Should match file1.txt, dirA, dirB (dirs), and file2.txt in both subdirs
        result = tool.run(base, "file2.txt dirA dirB", max_depth=2)
        results = set(result.strip().split("\n"))
        expected = {
            os.path.join(base, "dirA"),
            os.path.join(base, "dirB"),
            os.path.join(base, "dirA", "file2.txt"),
            os.path.join(base, "dirB", "file2.txt"),
        }
        assert expected.issubset(results)
    finally:
        teardown_test_dir(base)


def test_find_files_explicit_dir_pattern():
    base = setup_test_dir()
    try:
        tool = FindFilesTool()
        # Only directories, with trailing slash
        result = tool.run(base, "*/", max_depth=1)
        results = set(result.strip().split("\n"))
        expected = {
            os.path.join(base, "dirA") + os.sep,
            os.path.join(base, "dirB") + os.sep,
        }
        assert expected == results
    finally:
        teardown_test_dir(base)
