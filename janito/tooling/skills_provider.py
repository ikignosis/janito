"""
Skills provider for discovering and loading skills from the filesystem.

Based on Agent Skills progressive disclosure pattern:
1. Advertise (~100 tokens per skill) - names and descriptions in system prompt
2. Load (< 5000 tokens) - full SKILL.md content when skill is activated
3. Read resources - supplementary files when needed
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Any

from janito.tooling.reporter import report_start, report_result, report_error, report_warning


# Default skills directory
DEFAULT_SKILLS_DIR = Path.home() / ".janito" / "skills"


class Skill:
    """Represents a discovered skill."""
    
    def __init__(self, name: str, path: Path, description: str = "", content: str = ""):
        self.name = name
        self.path = path
        self.description = description
        self.content = content
        self.resources: Dict[str, Path] = {}
        
        # Discover resources in the skill directory
        self._discover_resources()
    
    def _discover_resources(self):
        """Scan skill directory for additional resources."""
        if not self.path.exists():
            return
        
        for item in self.path.iterdir():
            if item.is_file() and item.name != "SKILL.md":
                self.resources[item.name] = item
    
    def load_content(self) -> str:
        """Load the full SKILL.md content."""
        skill_md = self.path / "SKILL.md"
        if skill_md.exists():
            with open(skill_md, "r", encoding="utf-8") as f:
                self.content = f.read()
        return self.content
    
    def get_resource(self, resource_name: str) -> Optional[str]:
        """Get the content of a skill resource.
        
        Args:
            resource_name: Name of the resource file
            
        Returns:
            Content of the resource file, or None if not found
        """
        resource_path = self.path / resource_name
        if resource_path.exists() and resource_path.is_file():
            try:
                with open(resource_path, "r", encoding="utf-8") as f:
                    return f.read()
            except Exception:
                return None
        return None


class SkillsProvider:
    """
    Discovers and manages skills from filesystem directories.
    
    Searches configured paths recursively (up to two levels deep)
    for SKILL.md files.
    """
    
    def __init__(self, skill_paths: List[Path] = None):
        """
        Initialize the skills provider.
        
        Args:
            skill_paths: List of paths to search for skills.
                        Defaults to ~/.janito/skills
        """
        if skill_paths is None:
            skill_paths = [DEFAULT_SKILLS_DIR]
        
        self.skill_paths = skill_paths
        self._skills: Dict[str, Skill] = {}
        self._discover_skills()
    
    def _discover_skills(self):
        """Scan all skill paths for SKILL.md files."""
        for base_path in self.skill_paths:
            if not base_path.exists():
                continue
            
            # Search up to 2 levels deep for SKILL.md files
            for level1 in base_path.iterdir():
                if not level1.is_dir():
                    continue
                
                skill_md = level1 / "SKILL.md"
                if skill_md.exists():
                    # It's a skill directory
                    self._add_skill(level1.name, level1)
                    continue
                
                # Check one more level deep
                for level2 in level1.iterdir():
                    if not level2.is_dir():
                        continue
                    skill_md = level2 / "SKILL.md"
                    if skill_md.exists():
                        self._add_skill(level2.name, level2)
    
    def _add_skill(self, name: str, path: Path):
        """Add a skill to the provider."""
        # Extract description from SKILL.md if available
        description = ""
        skill_md = path / "SKILL.md"
        if skill_md.exists():
            try:
                with open(skill_md, "r", encoding="utf-8") as f:
                    content = f.read()
                    # Extract description from first paragraph
                    description = self._extract_description(content)
            except Exception:
                pass
        
        self._skills[name] = Skill(name, path, description)
    
    def _extract_description(self, content: str) -> str:
        """Extract a short description from SKILL.md content."""
        if not content:
            return ""
        
        # Skip YAML front matter if present
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                content = parts[2].strip()
        
        # Get first paragraph (non-empty lines)
        lines = content.split("\n")
        description_lines = []
        for line in lines:
            line = line.strip()
            if line.startswith("#"):
                continue  # Skip headers
            if line.startswith("```"):
                continue  # Skip code blocks
            if line:
                description_lines.append(line)
            if len(description_lines) >= 2:
                break
        
        description = " ".join(description_lines)
        # Truncate if too long
        if len(description) > 200:
            description = description[:197] + "..."
        
        return description
    
    def get_skill(self, name: str) -> Optional[Skill]:
        """Get a skill by name."""
        return self._skills.get(name)
    
    def list_skills(self) -> List[Dict[str, str]]:
        """List all discovered skills.
        
        Returns:
            List of dicts with 'name' and 'description' for each skill
        """
        result = []
        for name, skill in sorted(self._skills.items()):
            result.append({
                "name": name,
                "description": skill.description or "No description"
            })
        return result
    
    def get_advertisement(self) -> str:
        """
        Generate the skills advertisement section for system prompt.
        
        Returns:
            String with skill names and descriptions (~100 tokens per skill)
        """
        skills = self.list_skills()
        
        if not skills:
            return ""
        
        lines = ["\n\n## Available Skills", "Use these skills when the user's request matches their description:", ""]
        
        for skill in skills:
            lines.append(f"- **{skill['name']}**: {skill['description']}")
        
        return "\n".join(lines)
    
    def get_skill_tool_schemas(self) -> List[Dict[str, Any]]:
        """
        Get tool schemas for skill operations.
        
        Returns:
            List of tool schemas for load_skill and read_skill_resource
        """
        return [
            {
                "type": "function",
                "function": {
                    "name": "load_skill",
                    "description": "Load the full content of a skill's SKILL.md file. Call this when you need detailed instructions or guidance from a specific skill.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "skill_name": {
                                "type": "string",
                                "description": "The name of the skill to load (e.g., 'git-commit', 'code-review')"
                            }
                        },
                        "required": ["skill_name"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "read_skill_resource",
                    "description": "Read a supplementary resource file from a skill directory (e.g., templates, reference docs, examples).",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "skill_name": {
                                "type": "string",
                                "description": "The name of the skill"
                            },
                            "resource_name": {
                                "type": "string",
                                "description": "The filename of the resource to read (e.g., 'template.md', 'README.md', 'rules.txt')"
                            }
                        },
                        "required": ["skill_name", "resource_name"]
                    }
                }
            }
        ]


# Global skills provider instance
_global_skills_provider: Optional[SkillsProvider] = None


def get_skills_provider() -> SkillsProvider:
    """Get the global skills provider instance."""
    global _global_skills_provider
    if _global_skills_provider is None:
        _global_skills_provider = SkillsProvider()
    return _global_skills_provider


def load_skill(skill_name: str) -> str:
    """
    Tool function to load a skill's SKILL.md content.
    
    Args:
        skill_name: Name of the skill to load
        
    Returns:
        The full SKILL.md content, or error message if not found
    """
    report_start(f"Loading skill '{skill_name}'...", end="")
    
    provider = get_skills_provider()
    skill = provider.get_skill(skill_name)
    
    if skill is None:
        available = [s["name"] for s in provider.list_skills()]
        if available:
            error_msg = f"Skill '{skill_name}' not found. Available skills: {', '.join(available)}"
            report_error(error_msg)
            return error_msg
        error_msg = f"Skill '{skill_name}' not found. No skills are currently installed."
        report_error(error_msg)
        return error_msg
    
    content = skill.load_content()
    
    if not content:
        error_msg = f"Skill '{skill_name}' has no SKILL.md content."
        report_error(error_msg)
        return error_msg
    
    # Count lines for result message
    line_count = len(content.split('\n'))
    report_result(f"Loaded '{skill_name}' ({line_count} lines)")
    
    return f"# {skill_name}\n\n{content}"


def read_skill_resource(skill_name: str, resource_name: str) -> str:
    """
    Tool function to read a skill's resource file.
    
    Args:
        skill_name: Name of the skill
        resource_name: Filename of the resource to read
        
    Returns:
        The resource content, or error message if not found
    """
    report_start(f"Reading resource '{resource_name}' from skill '{skill_name}'...", end="")
    
    provider = get_skills_provider()
    skill = provider.get_skill(skill_name)
    
    if skill is None:
        available = [s["name"] for s in provider.list_skills()]
        if available:
            error_msg = f"Skill '{skill_name}' not found. Available skills: {', '.join(available)}"
            report_error(error_msg)
            return error_msg
        error_msg = f"Skill '{skill_name}' not found. No skills are currently installed."
        report_error(error_msg)
        return error_msg
    
    content = skill.get_resource(resource_name)
    
    if content is None:
        available = list(skill.resources.keys())
        if available:
            error_msg = f"Resource '{resource_name}' not found in skill '{skill_name}'. Available resources: {', '.join(available)}"
            report_error(error_msg)
            return error_msg
        error_msg = f"Resource '{resource_name}' not found in skill '{skill_name}'. This skill has no additional resources."
        report_error(error_msg)
        return error_msg
    
    # Count lines for result message
    line_count = len(content.split('\n'))
    report_result(f"Read resource '{resource_name}' from '{skill_name}' ({line_count} lines)")
    
    return f"# {skill_name}/{resource_name}\n\n{content}"


def get_skills_advertisement() -> str:
    """Get the skills advertisement for system prompt."""
    return get_skills_provider().get_advertisement()


def get_skills_tools() -> Dict[str, Any]:
    """Get skill-related tools as a dict mapping names to functions."""
    return {
        "load_skill": load_skill,
        "read_skill_resource": read_skill_resource,
    }
