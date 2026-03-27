"""
Example usage of the norm_path function from path_utils.
"""

import sys
from pathlib import Path

# Add the parent directory to sys.path to allow importing from tooling
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tooling.path_utils import norm_path

# Example 1: Current working directory
cwd = Path.cwd()
print(f"Current working directory: {norm_path(cwd)}")

# Example 2: Subdirectory of current working directory
subdir = cwd / "tooling" / "examples"
print(f"Subdirectory: {norm_path(subdir)}")

# Example 3: Unrelated path (will return unchanged)
unrelated = Path("/some/unrelated/path")
print(f"Unrelated path: {norm_path(unrelated)}")