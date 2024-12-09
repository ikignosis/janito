# 🤖 Janito CLI

A CLI tool for software development tasks powered by AI. Janito is your friendly AI-powered software development buddy that helps with coding tasks like refactoring, documentation updates, and code optimization.

## 📥 Installation

1. Install using pip:
```bash
pip install janito
```

2. Verify installation:
```bash
janito --version
```

## ⚙️ Setup

1. Get your Anthropic API key from [Anthropic's website](https://www.anthropic.com/)

2. Set your API key:
```bash
# Linux/macOS
export ANTHROPIC_API_KEY='your-api-key-here'

# Windows (Command Prompt)
set ANTHROPIC_API_KEY=your-api-key-here

# Windows (PowerShell)
$env:ANTHROPIC_API_KEY='your-api-key-here'
```

3. (Optional) Configure default test command:
```bash
export JANITO_TEST_CMD='pytest'  # or your preferred test command
```

## 🚀 Quick Start

### Basic Usage

```bash
# Add docstrings to your code
janito "add docstrings to this file"

# Optimize a function
janito "optimize the main function"

# Get code explanations
janito --ask "explain this code"
```

### Common Scenarios

1. **Code Refactoring**
```bash
# Refactor with test validation
janito "refactor this code to use list comprehension" --test "pytest"

# Refactor specific directory
janito "update imports" -i ./src
```

2. **Documentation Updates**
```bash
# Add or update docstrings
janito "add type hints and docstrings"

# Generate README
janito "create a README for this project"
```

3. **Code Analysis**
```bash
# Get code explanations
janito --ask "what does this function do?"

# Find potential improvements
janito --ask "suggest optimizations for this code"
```

## 🛠️ Command Reference

### Syntax
```bash
janito [OPTIONS] [REQUEST]
```

### Key Options

| Option | Description |
|--------|-------------|
| `REQUEST` | The AI request/instruction (in quotes) |
| `-w, --working-dir PATH` | Working directory [default: current] |
| `-i, --include PATH` | Include directory int the working context (can be multiple)|
| `--ask QUESTION` | Ask questions without making changes |
| `--test COMMAND` | Run tests before applying changes |
| `--debug` | Enable debug logging |
| `--verbose` | Enable verbose mode |
| `--version` | Show version information |
| `--help` | Show help message |

## 🔑 Key Features

- 🤖 AI-powered code analysis and modifications
- 💻 Interactive console mode
- ✅ Syntax validation for Python files
- 👀 Change preview and confirmation
- 🧪 Test command execution
- 📜 Change history tracking

## 📚 Additional Information

- Requires Python 3.8+
- Changes are backed up in `.janito/changes_history/`
- Environment variables:
  - `ANTHROPIC_API_KEY`: Required for API access
  - `JANITO_TEST_CMD`: Default test command (optional)

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.
