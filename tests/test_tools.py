import os
import sys
import tempfile
import subprocess


def run_janito_semantic(prompt):
    result = subprocess.run(
        [sys.executable, "-m", "janito", prompt],
        capture_output=True,
        text=True,
        errors="replace",  # Ensure decoding errors are replaced
    )
    return result


def test_create_and_append_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = os.path.join(tmpdir, "test.txt")
        result1 = run_janito_semantic(
            f"create the file {file_path} with content 'Hello'"
        )
        assert "create" in result1.stdout.lower() or "created" in result1.stdout.lower()
        result2 = run_janito_semantic(f"append ' World' to the file {file_path}")
        assert (
            "append" in result2.stdout.lower() or "appended" in result2.stdout.lower()
        )
        # Optionally, check for 'Hello World' in output if tool echoes content


def test_create_and_remove_directory():
    with tempfile.TemporaryDirectory() as tmpdir:
        dir_path = os.path.join(tmpdir, "subdir")
        result1 = run_janito_semantic(f"create a directory at {dir_path}")
        assert "create" in result1.stdout.lower() or "created" in result1.stdout.lower()
        result2 = run_janito_semantic(f"remove the directory {dir_path}")
        assert "remove" in result2.stdout.lower() or "removed" in result2.stdout.lower()


def test_remove_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = os.path.join(tmpdir, "toremove.txt")
        with open(file_path, "w", encoding="utf-8", errors="replace") as f:
            f.write("bye")
        result = run_janito_semantic(f"delete the file {file_path}")
        assert (
            "delete" in result.stdout.lower()
            or "deleted" in result.stdout.lower()
            or "remove" in result.stdout.lower()
        )


def test_move_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        src = os.path.join(tmpdir, "src.txt")
        dst = os.path.join(tmpdir, "dst.txt")
        with open(src, "w", encoding="utf-8", errors="replace") as f:
            f.write("move me")
        result = run_janito_semantic(f"move the file {src} to {dst}")
        assert "move" in result.stdout.lower() or "moved" in result.stdout.lower()


def test_replace_text_in_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = os.path.join(tmpdir, "replace.txt")
        with open(file_path, "w", encoding="utf-8", errors="replace") as f:
            f.write("foo bar baz")
        result = run_janito_semantic(
            f"replace 'bar' with 'qux' in the file {file_path}"
        )
        assert (
            "replace" in result.stdout.lower()
            or "replaced" in result.stdout.lower()
            or "qux" in result.stdout
        )


def test_run_bash_command():
    result = run_janito_semantic("run the bash command 'echo hello'")
    assert "hello" in result.stdout


def test_run_python_command():
    result = run_janito_semantic("run the python code print('hi')")
    assert "hi" in result.stdout


def test_find_files():
    with tempfile.TemporaryDirectory() as tmpdir:
        file1 = os.path.join(tmpdir, "a.txt")
        file2 = os.path.join(tmpdir, "b.py")
        open(file1, "w", encoding="utf-8", errors="replace").close()
        open(file2, "w", encoding="utf-8", errors="replace").close()
        result = run_janito_semantic(f"find all .py files in {tmpdir}")
        assert "b.py" in result.stdout or ".py" in result.stdout


def test_search_files():
    with tempfile.TemporaryDirectory() as tmpdir:
        file1 = os.path.join(tmpdir, "a.txt")
        with open(file1, "w", encoding="utf-8", errors="replace") as f:
            f.write("needle haystack needle")
        result = run_janito_semantic(f"search for 'needle' in files in {tmpdir}")
        assert "needle" in result.stdout


def test_run_bash_command_live_and_file_output():
    # Test both stdout and stderr, and large output
    # 1. Small output, both stdout and stderr
    result = run_janito_semantic("run the bash command 'echo hello && echo error 1>&2'")
    assert "hello" in result.stdout
    assert "error" in result.stdout or "error" in result.stderr

    # 2. Large output to trigger file path return (over 100 lines)
    result = run_janito_semantic(
        "run the bash command 'for i in $(seq 1 120); do echo line $i; done'"
    )
    # Should mention that output was saved to a temporary file and show some output lines
    assert "line 1" in result.stdout
    assert "line 120" in result.stdout
    assert "[LARGE OUTPUT]" in result.stdout
    assert "stdout_file:" in result.stdout
    assert "(lines: 120)" in result.stdout


def test_get_lines():
    with tempfile.TemporaryDirectory() as tmpdir:
        file1 = os.path.join(tmpdir, "lines.txt")
        with open(file1, "w", encoding="utf-8", errors="replace") as f:
            f.write("line1\nline2\nline3\n")
        result = run_janito_semantic(f"show line 2 of the file {file1}")
        # Accept either the actual line content or a confirmation message
        assert (
            ("line2" in result.stdout)
            or ("retrieve line 2" in result.stdout.lower())
            or ("read line 2" in result.stdout.lower())
        )
