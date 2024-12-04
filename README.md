# 🤖 Janito CLI

A CLI tool for software development tasks powered by AI.

Janito is an AI-powered assistant that helps automate common software development tasks like refactoring, documentation updates, and code optimization.

## 📥 Installation

```bash
# Install from PyPI
pip install janito

# Install from source
git clone https://github.com/joaompinto/janito.git
cd janito
pip install -e .
```

## ⚡ Requirements

- Python 3.8+
- Anthropic API key
- Required packages (automatically installed):
  - typer
  - pathspec
  - rich

## ⚙️ Configuration

### 🔑 API Key Setup
Janito requires an Anthropic API key to function. Set it as an environment variable:

```bash
export ANTHROPIC_API_KEY='your-api-key-here'
```

You can also add this to your shell profile (~/.bashrc, ~/.zshrc, etc.) for persistence.

## 📖 Usage

Janito can be used in two modes: Command Line or Interactive Console.

### 💻 Command Line Mode

```bash
janito REQUEST [OPTIONS]
```

#### Arguments
- `REQUEST`: The modification request

#### Options
- `-w, --workdir PATH`: Working directory (defaults to current directory)
- `--raw`: Print raw response instead of markdown format
- `--play PATH`: Replay a saved prompt file
- `-i, --include PATH`: Additional paths to include in analysis
- `--debug`: Show debug information
- `-v, --verbose`: Show verbose output
- `--ask`: Ask a question about the codebase
- `--scan`: Preview files that would be analyzed

### 🖥️ Interactive Console Mode

Start the interactive console by running `janito` without arguments:

```bash
janito
```

In console mode, you can:
- Enter requests directly
- Navigate history with up/down arrows
- Use special commands starting with /

### 📝 Examples

```bash
# Command Line Mode Examples
janito "create docstrings for all functions"
janito "add error handling" -w ./myproject
janito "update tests" -i ./tests -i ./lib
janito --ask "explain the authentication flow"
janito --scan  # Preview files to be analyzed

# Console Mode
janito  # Starts interactive session
```

## ✨ Features

- 🤖 AI-powered code analysis and modifications
- 💻 Interactive console mode for continuous interaction
- 📁 Support for multiple file types
- ✅ Syntax validation for Python files
- 👀 Interactive change preview and confirmation
- 📜 History tracking of all changes
- 🐛 Debug and verbose output modes
- ❓ Question-answering about codebase
- 🔍 File scanning preview

## 📚 History and Debugging

Changes are automatically saved in `.janito/history/` with timestamps:
- `*_analysis.txt`: Initial analysis
- `*_selected.txt`: Selected implementation
- `*_changes.txt`: Actual changes

Enable debug mode for detailed logging:
```bash
janito "request" --debug
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.