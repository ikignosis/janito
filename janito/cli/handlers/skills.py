"""
Handler functions for skill management.

Skills are extensions that provide additional tools and capabilities to the CLI.
They are typically installed from GitHub repositories in a specific format.
"""

import os
import re
import shutil
import tempfile
import subprocess
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple


# Path to store installed skills
SKILLS_DIR = Path.home() / ".janito" / "skills"


def _ensure_skills_dir() -> Path:
    """Ensure the skills directory exists."""
    SKILLS_DIR.mkdir(parents=True, exist_ok=True)
    return SKILLS_DIR


def _get_installed_skills() -> List[Dict[str, Any]]:
    """Scan the skills directory to find installed skills.
    
    Returns:
        List of skill entries with name and path
    """
    _ensure_skills_dir()
    skills = []
    for item in SKILLS_DIR.iterdir():
        if item.is_dir() and not item.name.startswith('.'):
            skills.append({
                "name": item.name,
                "path": str(item),
            })
    return sorted(skills, key=lambda s: s["name"])


def _parse_github_url(url: str) -> Tuple[str, str, str, str]:
    """Parse a GitHub URL to extract owner, repo, branch, and skill path.
    
    Args:
        url: GitHub URL (e.g., https://github.com/user/awesome-copilot/tree/main/skills/git-commit)
        
    Returns:
        Tuple of (owner, repo, branch, skill_path)
        
    Raises:
        ValueError: If the URL is not a valid GitHub URL
    """
    # Pattern: https://github.com/{owner}/{repo}/tree/{branch}/{path}
    pattern = r"(?:https?://)?github\.com/([^/]+)/([^/]+)/tree/([^/]+)/(.+)"
    match = re.match(pattern, url)
    
    if not match:
        raise ValueError(f"Invalid GitHub URL format: {url}")
    
    owner, repo, branch, skill_path = match.groups()
    return owner, repo, branch, skill_path


def _copy_dir(src: Path, dst: Path) -> None:
    """Copy a directory recursively to a destination.
    
    Args:
        src: Source directory
        dst: Destination directory
    """
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)


def handle_install_skill(url: str) -> int:
    """Install a skill from a GitHub URL.
    
    The URL should point to a skill directory in a GitHub repository.
    Example: https://github.com/user/awesome-copilot/tree/main/skills/git-commit
    
    For GitHub URLs:
    1. Parse the URL to extract owner, repo, branch, and skill path
    2. Clone the repository to a temporary directory
    3. Copy the skill directory to ~/.janito/skills/<skill-name>
    4. Register the skill in ~/.janito/skills/skills.json
    5. Clean up the temporary directory
    
    Args:
        url: GitHub URL to the skill
        
    Returns:
        Exit code (0 for success, non-zero for error)
    """
    print(f"Installing skill from: {url}")
    print()
    
    # Parse the GitHub URL
    try:
        owner, repo, branch, skill_path = _parse_github_url(url)
    except ValueError as e:
        print(f"Error: {e}")
        return 1
    
    skill_name = os.path.basename(skill_path)
    repo_url = f"https://github.com/{owner}/{repo}.git"
    
    print(f"Repository: {owner}/{repo}")
    print(f"Branch: {branch}")
    print(f"Skill path: {skill_path}")
    print(f"Skill name: {skill_name}")
    print()
    
    # Create a temporary directory for cloning
    temp_dir = tempfile.mkdtemp(prefix="janito_skill_")
    
    try:
        print(f"Cloning repository to temporary directory...")
        clone_cmd = ["git", "clone", "--depth", "1", "--branch", branch, repo_url, temp_dir]
        result = subprocess.run(
            clone_cmd,
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            print(f"Error cloning repository:")
            print(result.stderr)
            return 1
        
        print("Clone successful.")
        print()
        
        # Source and destination paths
        skill_src = Path(temp_dir) / skill_path
        skill_dst = SKILLS_DIR / skill_name
        
        # Validate skill directory exists
        if not skill_src.exists():
            print(f"Error: Skill directory not found: {skill_path}")
            return 1
        
        if not skill_src.is_dir():
            print(f"Error: Skill path is not a directory: {skill_path}")
            return 1
        
        # Copy skill to ~/.janito/skills/
        print(f"Copying skill to {skill_dst}...")
        _ensure_skills_dir()
        _copy_dir(skill_src, skill_dst)
        print("Copy successful.")
        print()
        print(f"[OK] Skill '{skill_name}' installed successfully!")
        
    except Exception as e:
        print(f"Error installing skill: {e}")
        return 1
    
    finally:
        # Clean up temporary directory (ignore errors on Windows)
        if os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
            except PermissionError:
                # On Windows, git files may be read-only; try with chmod
                import stat
                for root, dirs, files in os.walk(temp_dir):
                    for d in dirs:
                        try:
                            os.chmod(os.path.join(root, d), stat.S_IWUSR | stat.S_IRUSR)
                        except:
                            pass
                    for f in files:
                        try:
                            os.chmod(os.path.join(root, f), stat.S_IWUSR | stat.S_IRUSR)
                        except:
                            pass
                try:
                    shutil.rmtree(temp_dir)
                except:
                    pass
    
    return 0


def handle_list_skills(args) -> int:
    """List all installed skills.
    
    Args:
        args: Parsed command line arguments
        
    Returns:
        Exit code (0 for success)
    """
    skills = _get_installed_skills()
    
    if not skills:
        print("No skills installed.")
        print()
        print("Install a skill using:")
        print("  janito --install-skill https://github.com/user/repo/tree/main/skills/skill-name")
        return 0
    
    print(f"Installed skills ({len(skills)}):")
    print()
    
    for skill in skills:
        name = skill.get("name", "unknown")
        path = skill.get("path", "")
        
        print(f"  {name}")
        print(f"    Path: {path}")
        print()
    
    return 0


def handle_uninstall_skill(name: str) -> int:
    """Uninstall a skill by name.
    
    Args:
        name: Name of the skill to uninstall
        
    Returns:
        Exit code (0 for success, non-zero for error)
    """
    print(f"Uninstalling skill: {name}")
    print()
    
    # Scan for installed skills
    skills = _get_installed_skills()
    skill_names = [s["name"] for s in skills]
    
    if name not in skill_names:
        print(f"Error: Skill '{name}' not found.")
        print("Use --list-skills to see installed skills.")
        return 1
    
    # Remove skill directory
    skill_path = SKILLS_DIR / name
    
    if skill_path.exists():
        print(f"Removing skill files from {skill_path}...")
        shutil.rmtree(skill_path)
        print("[OK] Skill files removed.")
    else:
        print(f"Warning: Skill directory not found at {skill_path}")
    
    print()
    print(f"[OK] Skill '{name}' uninstalled successfully!")
    
    return 0
