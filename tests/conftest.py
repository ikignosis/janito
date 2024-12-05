import pytest
from pathlib import Path
import tempfile
import shutil

@pytest.fixture
def temp_workdir():
    """Create a temporary working directory for tests"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)

@pytest.fixture
def mock_files(temp_workdir):
    """Create mock files for testing"""
    # Create some test files
    (temp_workdir / "test.py").write_text("def test():\n    pass\n")
    (temp_workdir / "README.md").write_text("# Test Project\n")
    
    # Create nested directory structure
    nested_dir = temp_workdir / "src" / "project"
    nested_dir.mkdir(parents=True)
    (nested_dir / "main.py").write_text("print('hello')\n")
    
    return temp_workdir

@pytest.fixture
def mock_history_dir(temp_workdir):
    """Create a mock history directory"""
    history_dir = temp_workdir / ".janito" / "history"
    history_dir.mkdir(parents=True)
    return history_dir

@pytest.fixture
def mock_claude_response():
    """Mock Claude API response"""
    return {
        "analysis": """=== **Option 1**: Update test files
- Create basic test structure
- Add test fixtures
- Implement test cases""",
        "changes": """## abc123 tests/test_basic.py begin "Create basic test file" ##
def test_example():
    assert True
## abc123 tests/test_basic.py end ##"""
    }