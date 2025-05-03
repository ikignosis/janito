import tempfile
import os
from janito.agent.tools.python_file_runner import PythonFileRunnerTool


def test_python_file_runner_basic():
    tool = PythonFileRunnerTool()
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
        f.write('print("file runner test")')
        file_path = f.name
    try:
        result = tool.run(file_path)
        assert "file runner test" in result
        assert "Return code: 0" in result
    finally:
        os.remove(file_path)


def test_python_file_runner_error():
    tool = PythonFileRunnerTool()
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
        f.write('raise Exception("file error")')
        file_path = f.name
    try:
        result = tool.run(file_path)
        assert "Exception" in result or "file error" in result
        assert "Return code:" in result
    finally:
        os.remove(file_path)
