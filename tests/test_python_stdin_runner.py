from janito.agent.tools.python_stdin_runner import PythonStdinRunnerTool


def test_python_stdin_runner_basic():
    tool = PythonStdinRunnerTool()
    code = 'print("stdin runner test")'
    result = tool.run(code)
    assert "stdin runner test" in result
    assert "Return code: 0" in result


def test_python_stdin_runner_empty():
    tool = PythonStdinRunnerTool()
    result = tool.run("")
    assert "Warning: Empty code provided" in result


def test_python_stdin_runner_error():
    tool = PythonStdinRunnerTool()
    code = 'raise RuntimeError("stdin fail")'
    result = tool.run(code)
    assert "RuntimeError" in result or "stdin fail" in result
    assert "Return code:" in result
