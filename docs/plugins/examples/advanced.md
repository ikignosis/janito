# Advanced Plugin Example

## Overview

This example demonstrates a sophisticated plugin that provides multiple interconnected tools, custom commands, and advanced configuration. It showcases the full capabilities of the Janito plugin system.

## Plugin Code

```python
from janito.plugins.base import Plugin, PluginMetadata, PluginResource
from janito.tools.tool_base import ToolBase, ToolPermissions
from janito.cli.core import Runner
from typing import Dict, Any, List
import json
import os

class ProjectManagerTool(ToolBase):
    tool_name = "project_create"
    permissions = ToolPermissions(read=True, write=True, execute=True)
    
    def run(self, name: str, template: str = "basic", directory: str = ".") -> str:
        """Create a new project from a template."""
        templates = {
            "basic": {"files": ["README.md", "main.py"]},
            "web": {"files": ["index.html", "style.css", "script.js"]},
            "python": {"files": ["__init__.py", "main.py", "tests/", ".gitignore"]}
        }
        
        if template not in templates:
            return f"Error: Unknown template '{template}'. Available templates: {list(templates.keys())}"
        
        project_path = os.path.join(directory, name)
        
        if os.path.exists(project_path):
            return f"Error: Project directory '{project_path}' already exists"
        
        try:
            os.makedirs(project_path)
            
            # Create files from template
            for item in templates[template]["files"]:
                item_path = os.path.join(project_path, item)
                if item.endswith("/""" or os.path.isdir(item):
                    os.makedirs(item_path, exist_ok=True)
                else:
                    with open(item_path, "w") as f:
                        if item == "README.md":
                            f.write(f"# {name}\n\nGenerated project from '{template}' template.\n")
                        elif item == "main.py":
                            f.write("# Main application code\n")
            
            return f"Project '{name}' created successfully at '{project_path}' using '{template}' template."
            
        except Exception as e:
            return f"Error creating project: {str(e)}"

class ProjectListTool(ToolBase):
    tool_name = "project_list"
    permissions = ToolPermissions(read=True, write=False, execute=True)
    
    def run(self, directory: str = ".") -> str:
        """List projects in a directory."""
        try:
            projects = []
            for item in os.listdir(directory):
                item_path = os.path.join(directory, item)
                if os.path.isdir(item_path) and os.path.exists(os.path.join(item_path, "janito.json")):
                    projects.append(item)
            
            if not projects:
                return f"No projects found in '{directory}'"
            
            return f"Projects in '{directory}':\n" + "\n".join(f"- {p}" for p in projects)
            
        except Exception as e:
            return f"Error listing projects: {str(e)}"

class ProjectConfigTool(ToolBase):
    tool_name = "project_configure"
    permissions = ToolPermissions(read=True, write=True, execute=True)
    
    def run(self, project: str, key: str, value: str, directory: str = ".") -> str:
        """Configure a project's settings."""
        project_path = os.path.join(directory, project)
        config_path = os.path.join(project_path, "janito.json")
        
        if not os.path.exists(config_path):
            return f"Error: Project '{project}' not found or not a Janito project"
        
        try:
            # Read existing config
            config = {}
            if os.path.exists(config_path):
                with open(config_path, "r") as f:
                    config = json.load(f)
            
            # Update configuration
            if "project" not in config:
                config["project"] = {}
            
            # Handle nested keys (e.g., "database.host")
            keys = key.split(".")
            current = config["project"]
            for k in keys[:-1]:
                if k not in current:
                    current[k] = {}
                current = current[k]
            
            # Set the final value (try to parse as JSON, otherwise treat as string)
            try:
                parsed_value = json.loads(value)
                current[keys[-1]] = parsed_value
            except json.JSONDecodeError:
                current[keys[-1]] = value
            
            # Write updated config
            with open(config_path, "w") as f:
                json.dump(config, f, indent=2)
            
            return f"Configuration updated: {key} = {value}"
            
        except Exception as e:
            return f"Error configuring project: {str(e)}"

class AdvancedPlugin(Plugin):
    def __init__(self):
        super().__init__()
        self.project_manager = None
        self.project_list = None
        self.project_config = None
    
    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="advanced",
            version="1.0.0",
            description="Advanced project management plugin",
            author="Janito Team",
            license="MIT",
            homepage="https://github.com/janito/plugins/advanced",
            dependencies=[]
        )
    
    def get_tools(self):
        return [ProjectManagerTool, ProjectListTool, ProjectConfigTool]
    
    def get_commands(self) -> Dict[str, Any]:
        """Add custom CLI commands."""
        return {
            "project-create": self._cli_project_create,
            "project-list": self._cli_project_list,
            "project-configure": self._cli_project_configure
        }
    
    def _cli_project_create(self, runner: Runner, args: List[str]) -> str:
        """CLI command to create a project."""
        if len(args) < 1:
            return "Usage: project-create <name> [template] [directory]"
        
        name = args[0]
        template = args[1] if len(args) > 1 else "basic"
        directory = args[2] if len(args) > 2 else "."
        
        tool = ProjectManagerTool()
        return tool.run(name, template, directory)
    
    def _cli_project_list(self, runner: Runner, args: List[str]) -> str:
        """CLI command to list projects."""
        directory = args[0] if args else "."
        
        tool = ProjectListTool()
        return tool.run(directory)
    
    def _cli_project_configure(self, runner: Runner, args: List[str]) -> str:
        """CLI command to configure a project."""
        if len(args) < 3:
            return "Usage: project-configure <project> <key> <value> [directory]"
        
        project = args[0]
        key = args[1]
        value = args[2]
        directory = args[3] if len(args) > 3 else "."
        
        tool = ProjectConfigTool()
        return tool.run(project, key, value, directory)
    
    def get_config_schema(self) -> Dict[str, Any]:
        """Return JSON schema for plugin configuration."""
        return {
            "type": "object",
            "properties": {
                "default_template": {
                    "type": "string",
                    "description": "Default project template",
                    "enum": ["basic", "web", "python"],
                    "default": "basic"
                },
                "projects_directory": {
                    "type": "string",
                    "description": "Default directory for projects",
                    "default": "./projects"
                }
            }
        }
    
    def get_resources(self) -> List[PluginResource]:
        """List all resources provided by this plugin."""
        return [
            PluginResource(
                name="project_create",
                type="tool",
                description="Create new projects from templates"
            ),
            PluginResource(
                name="project_list",
                type="tool",
                description="List existing projects"
            ),
            PluginResource(
                name="project_configure",
                type="tool",
                description="Configure project settings"
            ),
            PluginResource(
                name="project-create",
                type="command",
                description="CLI command to create projects"
            ),
            PluginResource(
                name="project-list",
                type="command",
                description="CLI command to list projects"
            ),
            PluginResource(
                name="project-configure",
                type="command",
                description="CLI command to configure projects"
            ),
            PluginResource(
                name="advanced_config",
                type="config",
                description="Configuration schema for advanced plugin"
            )
        ]
    
    def initialize(self):
        """Initialize the plugin."""
        self.project_manager = ProjectManagerTool()
        self.project_list = ProjectListTool()
        self.project_config = ProjectConfigTool()
        
        # Apply configuration
        config = self.get_config()
        if config:
            # Store configuration for later use
            self._config = config
    
    def cleanup(self):
        """Cleanup resources when plugin is unloaded."""
        self.project_manager = None
        self.project_list = None
        self.project_config = None

# Register the plugin
class PLUGIN_CLASS(AdvancedPlugin):
    pass
```

## Configuration

```json
{
  "plugins": {
    "load": {
      "advanced": true
    },
    "config": {
      "advanced": {
        "default_template": "python",
        "projects_directory": "./my-projects"
      }
    }
  }
}
```

## Usage

### Using Tools

```json
{
  "tool": "project_create",
  "name": "my-web-app",
  "template": "web"
}
```

```json
{
  "tool": "project_configure",
  "project": "my-web-app",
  "key": "database.host",
  "value": "localhost"
}
```

### Using CLI Commands

```bash
janito project-create my-api python ./projects
janito project-list ./projects
janito project-configure my-api database.port "5432"
```

## Key Concepts Demonstrated

- **Multiple Tools**: A plugin providing several related tools
- **Custom Commands**: Adding CLI commands that integrate with the main interface
- **Complex Configuration**: Handling nested configuration keys and JSON values
- **File System Operations**: Creating directories and files
- **Resource Declaration**: Explicitly defining all provided resources (tools, commands, config)
- **Plugin State**: Maintaining state between method calls
- **Error Handling**: Comprehensive error handling for various failure modes
- **CLI Integration**: Creating user-friendly command-line interfaces

This advanced example demonstrates the full potential of the plugin system, showing how to create sophisticated extensions that deeply integrate with the Janito ecosystem.