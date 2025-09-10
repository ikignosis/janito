# Installation Guide

This guide explains how to install Janito and verify your setup.

## Requirements

- Python 3.10 or newer
- **Terminal**: Windows Terminal (primary supported), PowerShell, Command Prompt, or any Unicode-capable terminal emulator
- **Shell Support**: Bash (for `run_bash_command` tool) and/or PowerShell (for `run_powershell_command` tool) depending on your platform and intended usage

## Installation Methods

You can install Janito using pip from either PyPI (for stable releases) or directly from GitHub (for the latest development version).

### From PyPI (Stable)
```bash
uv pip install janito
```

### From GitHub (Development Version)
```bash
uv pip install git+git@github.com:ikignosis/janito.git
```

> For development setup and contributing, see [Developing & Extending](developing.md).

## Verifying Your Installation

To confirm Janito is installed correctly, run:

```bash
janito --help
```

You should see the Janito CLI help message.

## Related Guides

- [Configuration Guide](configuration.md)
- [Usage Guide](using.md)
- [Developing & Extending](developing.md)
