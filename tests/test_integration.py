import pytest
from pathlib import Path
from janito.__main__ import typer_main
from janito.agents import AIAgent

class MockClaudeAgent:
    def __init__(self, responses=None):
        self.responses = responses or {}
        self.messages_history = []
    
    def send_message(self, message):
        self.messages_history.append(("user", message))
        # Return mock response or empty string
        response = self.responses.get(message, "")
        self.messages_history.append(("assistant", response))
        return response

def test_basic_workflow(temp_workdir, monkeypatch, capsys):
    """Test basic workflow with mocked Claude responses"""
    # Mock responses
    mock_responses = {
        "analysis": """=== **Option 1**: Create test file
- Add basic test structure
- Include fixtures""",
        "implementation": """## abc123 test_sample.py begin "Create test file" ##
def test_example():
    assert True
## abc123 test_sample.py end ##"""
    }
    
    mock_agent = MockClaudeAgent(mock_responses)
    monkeypatch.setattr("janito.agent.AIAgent", lambda **kwargs: mock_claude)
    
    # Run command
    typer_main(["create test file"], workdir=temp_workdir)
    
    # Verify output
    captured = capsys.readouterr()
    assert "Option 1" in captured.out
    
    # Verify file creation
    assert (temp_workdir / "test_sample.py").exists()

def test_scan_workflow(temp_workdir, mock_files, capsys):
    """Test file scanning functionality"""
    typer_main(["--scan"], workdir=mock_files)
    
    # Verify output contains expected files
    captured = capsys.readouterr()
    assert "test.py" in captured.out
    assert "README.md" in captured.out
    assert "src/project/main.py" in captured.out

def test_history_creation(temp_workdir, mock_claude_response, monkeypatch):
    """Test history file creation during workflow"""
    mock_agent = MockClaudeAgent({"test": mock_claude_response["analysis"]})
    monkeypatch.setattr("janito.agent.AIAgent", lambda **kwargs: mock_claude)
    
    typer_main(["test"], workdir=temp_workdir)
    
    # Verify history directory creation
    history_dir = temp_workdir / ".janito" / "history"
    assert history_dir.exists()
    assert any(history_dir.iterdir())