# 🤖 Janito

Janito is a powerful AI-assisted command-line interface (CLI) tool built with Python, leveraging Anthropic's Claude for intelligent code and file management.

[![GitHub Repository](https://img.shields.io/badge/GitHub-Repository-blue?logo=github)](https://github.com/joaompinto/janito)

## ✨ Features

- 🧠 Intelligent AI assistant powered by Claude
- 📁 File management capabilities with real-time output
- 🔍 Smart code search and editing
- 💻 Interactive terminal interface with rich formatting
- 📊 Detailed token usage tracking and cost reporting with cache savings analysis
- 🛑 Token and tool usage reporting even when interrupted with Ctrl+C
- 🌐 Web page fetching with content extraction capabilities
- 🔄 Parameter profiles for optimizing Claude's behavior for different tasks
- 📋 Line delta tracking to monitor net changes in files

## 🛠️ Installation

```bash
# Install directly from PyPI
pip install janito
```

For development or installation from source, please see [README_DEV.md](README_DEV.md).

## 🚀 Usage

After installation, you can use the `janito` command in your terminal:

```bash
# Get help
janito --help

# Ask the AI assistant a question
janito "Suggest improvements to this project"

# Add a feature to the CLI
janito "Add a --version to the cli to report the version"

# Show detailed token usage and cost information
janito --show-tokens "Explain how to optimize Python code"

# Use a specific parameter profile
janito --profile creative "Write a short story about AI"

# Continue previous conversation
janito --continue "Can you elaborate on that last point?"

# Show current configuration and available profiles
janito --show-config

# You can press Ctrl+C at any time to interrupt a query
# Janito will still display token and tool usage information
```

## 🔧 Available Tools

Janito comes with several built-in tools:
- 📄 `str_replace_editor` - View, create, and edit files
- 🔎 `find_files` - Find files matching patterns
- 🗑️ `delete_file` - Delete files
- 🔍 `search_text` - Search for text patterns in files
- 🌐 `fetch_webpage` - Fetch and extract content from web pages
- 📋 `move_file` - Move files from one location to another
- 💻 `bash` - Execute bash commands with real-time output display

## 📊 Usage Tracking

Janito includes a comprehensive token usage tracking system that helps you monitor API costs:

- **Basic tracking**: By default, Janito displays a summary of token usage and cost after each query
- **Detailed reporting**: Use the `--show-tokens` or `-t` flag to see detailed breakdowns including:
  - Input and output token counts
  - Per-tool token usage statistics
  - Precise cost calculations
  - Cache performance metrics with savings analysis
  - Line delta tracking for file modifications

```bash
# Show detailed token usage and cost information
janito --show-tokens "Write a Python function to sort a list"

# Basic usage (shows simplified token usage summary)
janito "Explain Docker containers"
```

The usage tracker automatically calculates cache savings, showing you how much you're saving by reusing previous responses.

## 📋 Parameter Profiles

Janito offers predefined parameter profiles to optimize Claude's behavior for different tasks:

- **precise**: Factual answers, documentation, structured data (temperature: 0.2)
- **balanced**: Professional writing, summarization, everyday tasks (temperature: 0.5)
- **conversational**: Natural dialogue, educational content (temperature: 0.7)
- **creative**: Storytelling, brainstorming, marketing copy (temperature: 0.9)
- **technical**: Code generation, debugging, technical problem-solving (temperature: 0.3)

```bash
# Use a specific profile
janito --profile creative "Write a poem about coding"

# View available profiles
janito --show-config
```

## ⚙️ Requirements

- Python 3.8 or higher
- Dependencies:
  - typer (>=0.9.0)
  - rich (>=13.0.0)
  - claudine (for Claude AI integration)
- For Windows users:
  - Git Bash is required for proper operation of the CLI tools

## 🔑 API Key

Janito requires an Anthropic API key to function. You can:
1. Set it as an environment variable: `export ANTHROPIC_API_KEY=your_api_key`
2. Set it globally: `janito --set-api-key your_api_key`
3. Or enter it when prompted

## 💻 Development

For development instructions, please refer to [README_DEV.md](README_DEV.md).

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.