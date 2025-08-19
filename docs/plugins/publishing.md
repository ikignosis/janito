# Publishing Plugins

## Overview

This guide explains how to publish and share your plugins with the Janito community. Publishing your plugins allows others to benefit from your work and contributes to the ecosystem.

## Preparation

Before publishing, ensure your plugin is ready for distribution:

### Code Quality
- **Testing**: Include comprehensive tests in a `tests/` directory
- **Documentation**: Provide clear documentation in your plugin directory
- **Code Style**: Follow PEP 8 and project coding standards
- **Error Handling**: Implement robust error handling

### Metadata
Ensure your plugin metadata is complete and accurate:

```python
def get_metadata(self) -> PluginMetadata:
    return PluginMetadata(
        name="myplugin",                    # Unique, descriptive name
        version="1.0.0",                   # Follow semantic versioning
        description="A useful plugin",     # Clear, concise description
        author="Your Name",                # Your name or organization
        license="MIT",                     # Choose an appropriate license
        homepage="https://github.com/yourusername/myplugin",  # Project URL
        dependencies=["requests>=2.25.0"]  # List dependencies
    )
```

### Configuration
Provide a clear configuration schema:

```python
def get_config_schema(self) -> Dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "api_key": {
                "type": "string",
                "description": "Your API key for the service",
                "minLength": 32
            }
        },
        "required": ["api_key"]
    }
```

## Publishing Options

### Option 1: Official Plugins Repository

The recommended way to publish plugins is to contribute to the official repository:

1. **Fork the Repository**: Fork `https://github.com/ikignosis/janito-plugins`
2. **Add Your Plugin**: Create a directory for your plugin in the appropriate category
3. **Submit Pull Request**: Submit a PR with your plugin

```
janito-plugins/
├── core/           # Core functionality plugins
├── dev/            # Development tools
├── web/            # Web-related plugins
├── ui/             # User interface plugins
└── community/      # Community-contributed plugins
    └── yourplugin/ # Your plugin directory
```

### Option 2: Personal Repository

Publish your plugin in your own GitHub repository:

1. **Create Repository**: Create a new repository (e.g., `janito-myplugin`)
2. **Organize Structure**:

```
janito-myplugin/
├── plugins/
│   └── myplugin/
│       ├── __init__.py
│       └── tools/
│           └── mytool.py
├── docs/
│   └── README.md
├── tests/
│   └── test_myplugin.py
├── setup.py
└── README.md
```

3. **Add Installation Instructions**:

```markdown
## Installation

1. Add to your `janito.json`:

```json
{
  "plugins": {
    "repository": {
      "url": "https://github.com/yourusername/janito-myplugin.git"
    }
  }
}
```
```

### Option 3: PyPI Package

Package your plugin as a Python package:

1. **Create setup.py**:

```python
from setuptools import setup, find_packages

setup(
    name="janito-myplugin",
    version="1.0.0",
    description="My Janito plugin",
    packages=find_packages(),
    install_requires=[
        "janito>=2.0.0",
        "requests>=2.25.0"
    ],
    entry_points={
        "janito.plugins": [
            "myplugin = plugins.myplugin:PLUGIN_CLASS"
        ]
    }
)
```

2. **Publish to PyPI**:

```bash
# Build the package
python setup.py sdist bdist_wheel

# Upload to PyPI
pip install twine
twine upload dist/*
```

3. **Installation**:

```bash
pip install janito-myplugin
```

## Repository Structure

When publishing, follow this recommended structure:

```
myplugin/
├── plugins/
│   └── myplugin/
│       ├── __init__.py           # Plugin interface
│       └── tools/
│           └── *.py              # Tool implementations
├── docs/
│   ├── README.md               # Plugin documentation
│   └── examples.md               # Usage examples
├── tests/
│   └── test_*.py               # Test files
├── .github/
│   └── workflows/
│       └── test.yml            # CI/CD configuration
├── pyproject.toml              # Modern Python packaging
├── README.md                   # Project overview
└── LICENSE                     # License file
```

## Documentation Requirements

Include comprehensive documentation:

### README.md

```markdown
# MyPlugin

## Description

A brief description of what your plugin does and why it's useful.

## Features

- Feature 1
- Feature 2
- Feature 3

## Installation

Instructions for installing and enabling the plugin.

## Usage

Examples of how to use the plugin's tools and commands.

## Configuration

Details about configuration options and their defaults.

## License

The license under which the plugin is distributed.
```

### Usage Examples

Provide clear examples in your documentation:

```json
{
  "tool": "mytool",
  "parameter": "value"
}
```

## Versioning

Follow semantic versioning (MAJOR.MINOR.PATCH):

- **MAJOR**: Incompatible API changes
- **MINOR**: Backward-compatible functionality additions
- **PATCH**: Backward-compatible bug fixes

Update your version in both the code and documentation when releasing new versions.

## Community Guidelines

When contributing to the official repository:

- **Code Review**: Be open to feedback and suggestions
- **Responsiveness**: Respond to issues and PRs in a timely manner
- **Maintenance**: Keep your plugin updated and compatible
- **Support**: Provide reasonable support for users

## Promotion

Once published, promote your plugin:

- **Social Media**: Share on relevant platforms
- **Forums**: Post in developer communities
- **Documentation**: Add to the official plugins list
- **Showcase**: Include in plugin showcases

Publishing your plugins helps grow the Janito ecosystem and benefits the entire community.