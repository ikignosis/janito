# Aurora: Natural Language Code Editing Agent

Aurora is a command-line and web-based AI agent designed to **edit code and manage files** using natural language instructions.

---

## Key Features
- **Code Editing via Natural Language:** Modify, create, or delete code files simply by describing the changes.
- **File & Directory Management:** Navigate, create, move, or remove files and folders.
- **Context-Aware:** Understands your project structure for precise edits.
- **Interactive User Prompts:** Asks for clarification when needed.
- **Extensible Tooling:** Built-in tools for file operations, shell commands, and more.
- **Web Interface:** Stream responses and tool progress via a simple web UI.

---

## Installation

### Requirements
- Python 3.8+

### Install dependencies
```bash
pip install -e .
```

### Set your API key
Aurora uses OpenAI-compatible APIs (default: `openrouter/quasar-alpha`). Set your API key as an environment variable:
```bash
export OPENAI_API_KEY=your_api_key_here
```

---

## Usage

### Command Line Interface
Run Aurora in single prompt mode:
```bash
python -m aurora "Refactor the data processing module to improve readability."
```

Interactive chat mode:
```bash
python -m aurora --chat
```

### Web Server
Start the web server (default port 5000):
```bash
python -m aurora.web
```
Or specify a port:
```bash
python -m aurora.web 8080
```

Then open `http://localhost:5000` (or your port) in a browser.

---

## Project Structure
See `docs/structure.md` for detailed file descriptions.

---

## License
MIT License

---

## Author
João Pinto
