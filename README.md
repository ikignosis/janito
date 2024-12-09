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

## 📖 Command Reference

### Basic Syntax

```bash
janito [OPTIONS] [REQUEST]
```

### Command Options

| Option | Description |
|--------|-------------|
| `REQUEST` | The AI request/instruction (in quotes) |
| `-w, --working-dir PATH` | Specify working directory [default: current directory] |
| `--ask` | Ask questions about code without making changes |
| `--test COMMAND` | Run specified test command before applying changes |
| `--debug` | Enable debug mode for detailed logging |
| `--help` | Show help message and exit |

### Usage Examples

```bash
# Basic usage - modify code
janito "add docstrings"
janito "optimize this function"
janito "add error handling"

# Specify working directory
janito "update imports" -w ./src

# Ask questions without changes
janito --ask "explain this code"
janito --ask "what does this function do?"

# Run tests before applying changes
janito "refactor code" --test "pytest"
janito "optimize function" --test "python -m unittest"

# Debug mode
janito "update logging" --debug

# Skip confirmations and syntax checking
janito "format code" --no-confirm --no-syntax-check

# Check version
janito --version

# Get help
janito --help
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
- Environment variables:
  - `ANTHROPIC_API_KEY`: Required for API access
  - `JANITO_TEST_CMD`: Default test command (optional)

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.
