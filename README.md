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

## ⚙️ Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ANTHROPIC_API_KEY` | Anthropic API key for Claude AI | Required |
| `JANITO_TEST_CMD` | Default test command | None |
| `AI_BACKEND` | AI backend to use (claudeai/openai) | claudeai |

## 🎯 Command Line Options

### Core Options

| Option | Description |
|--------|-------------|
| `REQUEST` | Change request or command to execute |
| `-w, --workdir` | Set working directory |
| `-i, --include` | Additional paths to include |
| `--debug` | Show debug information |
| `--verbose` | Show verbose output |
| `--version` | Show version information |

### Operation Modes

| Option | Description |
|--------|-------------|
| `--ask` | Ask questions about codebase |
| `--play` | Replay saved prompt file |
| `--scan` | Preview files to analyze |
| `--input` | Read request from stdin |
| `--history` | Display request history |

### Execution Control

| Option | Description |
|--------|-------------|
| `--test` | Command to run tests |
| `--auto-apply` | Apply changes without confirmation |
| `--tui` | Use terminal user interface |

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

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.