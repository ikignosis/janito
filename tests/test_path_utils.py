"""
Test script for the path_utils module.
"""

import sys
from pathlib import Path

# Add the repo root to sys.path to allow importing the package directly.
sys.path.insert(0, str(Path(__file__).parent.parent))

from janito.tooling.path_utils import display_path, norm_path


def test_norm_path():
    """Test the norm_path function with various scenarios."""
    cwd = Path.cwd().resolve()

    # Test 1: Path exactly matches current working directory
    result1 = norm_path(cwd)
    print(f"Test 1 - CWD: {result1}")
    assert result1 == str(cwd), f"Expected {cwd}, got {result1}"

    # Test 2: Path is a subpath of working directory
    subpath = cwd / "some" / "subdir"
    result2 = norm_path(subpath)
    expected2 = "./some/subdir"
    print(f"Test 2 - Subpath: {result2}")
    assert result2 == expected2, f"Expected {expected2}, got {result2}"

    # Test 3: Path is not related to working directory (should return unchanged)
    unrelated_path = Path("/unrelated/path")
    result3 = norm_path(unrelated_path)
    print(f"Test 3 - Unrelated: {result3}")
    # On Windows, the unrelated path will use backslashes, but that's fine
    # as we're not modifying unrelated paths
    assert result3 == str(unrelated_path), f"Expected {unrelated_path}, got {result3}"

    # Test 4: String input (should work the same)
    result4 = norm_path(str(cwd / "another" / "subdir"))
    expected4 = "./another/subdir"
    print(f"Test 4 - String input: {result4}")
    assert result4 == expected4, f"Expected {expected4}, got {result4}"

    print("All tests passed!")


def test_display_path_maps_home_to_tilde(monkeypatch, tmp_path):
    """Paths under the home directory are shown as ~/relative."""
    home = tmp_path / "home"
    project = home / "project"
    project.mkdir(parents=True)
    monkeypatch.setenv("HOME", str(home))

    assert display_path(project) == "~/project"
    assert display_path(str(project)) == "~/project"


def test_display_path_maps_home_itself_to_tilde(monkeypatch, tmp_path):
    """The home directory itself is shown as ~."""
    home = tmp_path / "home"
    home.mkdir(parents=True)
    monkeypatch.setenv("HOME", str(home))

    assert display_path(home) == "~"


def test_display_path_leaves_other_paths_unchanged(monkeypatch, tmp_path):
    """Paths outside the home directory are left unchanged."""
    home = tmp_path / "home"
    home.mkdir(parents=True)
    monkeypatch.setenv("HOME", str(home))

    outside = tmp_path / "outside"
    assert display_path(outside) == str(outside.resolve())


if __name__ == "__main__":
    test_norm_path()
