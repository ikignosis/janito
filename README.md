# 🤖 Janito

Janito is a powerful AI-assisted command-line interface (CLI) tool built with Python, leveraging Anthropic's Claude for intelligent code and file management.

## ✨ Features

- 🧠 Intelligent AI assistant powered by Claude
- 📁 File management capabilities 
- 🔍 Smart code search and editing
- 💻 Interactive terminal interface with rich formatting
- 📊 Token usage tracking and cost reporting

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

janito "Add a --version to the cli to report he version"

```

## 🔧 Available Tools

Janito comes with several built-in tools:
- 📄 `str_replace_editor` - View, create, and edit files
- 🔎 `find_files` - Find files matching patterns
- 🗑️ `delete_file` - Delete files
- 🔍 `search_text` - Search for text patterns in files

## ⚙️ Requirements

- Python 3.8 or higher
- Dependencies:
  - typer (>=0.9.0)
  - rich (>=13.0.0)
  - claudine (for Claude AI integration)

## 🔑 API Key

Janito requires an Anthropic API key to function. You can:
1. Set it as an environment variable: `export ANTHROPIC_API_KEY=your_api_key`
2. Or enter it when prompted

## 💻 Development

```bash
# Create a virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install development dependencies
pip install -e ".[dev]"
```

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.