# 🤖 Janito CLI

A CLI tool for software development tasks powered by AI. Janito is your friendly AI-powered software development buddy that helps with coding tasks like refactoring, documentation updates, and code optimization.

## 📥 Installation

```bash
pip install janito  # Install from PyPI
```

## ⚙️ Setup

1. Set your Anthropic API key:
```bash
export ANTHROPIC_API_KEY='your-api-key-here'
```

2. (Optional) Configure a test command:
```bash
export JANITO_TEST_CMD='your-test-command'
```

## 📖 Quick Start

### Command Line Mode

```bash
janito "add docstrings"                    # Basic usage
janito "update error handling" -w ./src    # Specify working directory
janito --ask "explain this function"       # Ask questions about code
janito "refactor code" --test "pytest"     # Run tests before applying changes
```

### Interactive Console Mode

```bash
janito  # Start interactive session
```

## 🔑 Key Features

- 🤖 AI-powered code analysis and modifications
- 💻 Interactive console mode
- ✅ Syntax validation for Python files
- 👀 Change preview and confirmation
- 🧪 Test command execution
- 📜 Change history tracking

## 📚 Additional Information

- Python 3.8+ required
- Changes saved in `.janito/history/`
- Debug mode: `janito "request" --debug`

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.
