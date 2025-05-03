from janito.agent.tools.python_command_runner import PythonCommandRunnerTool


def test_python_command_runner_basic():
    tool = PythonCommandRunnerTool()
    code = 'print("hello world")'
    result = tool.run(code)
    assert "hello world" in result
    assert "Return code: 0" in result


def test_python_command_runner_empty():
    tool = PythonCommandRunnerTool()
    result = tool.run("")
    assert "Warning: Empty code provided" in result


def test_python_command_runner_error():
    tool = PythonCommandRunnerTool()
    code = 'raise ValueError("fail")'
    result = tool.run(code)
    assert "ValueError" in result or "fail" in result
    assert "Return code:" in result
