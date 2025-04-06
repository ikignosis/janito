# Aurora: Natural Language Code Editing Agent

Aurora is a command-line AI agent designed to **edit code and manage files** using natural language instructions, powered by the `openrouter/quasar-alpha` model.

## Key Capabilities

- **Code Editing via Natural Language:** Modify, create, replace, or delete code files simply by describing the changes you want.
- **File & Directory Management:** Seamlessly navigate, create, or remove files and folders within your project.
- **Context-Aware Modifications:** Aurora understands your project structure to perform precise edits.
- **Interactive User Prompts:** When clarification is needed, Aurora asks you before making changes.
- **Extensible Tooling:** Built-in tools for file operations, with the ability to add more.

## Built-in Tools

Aurora leverages a rich set of tools to perform project operations:

- **File Operations:**
  - View file contents or list directory contents
  - Create or overwrite files
  - Replace content in existing files
  - Remove files
- **Directory Management:**
  - Create new directories
- **Search & Discovery:**
  - Search for text patterns within files
  - Find files matching patterns recursively
- **Execution:**
  - Run Bash commands
- **User Interaction:**
  - Prompt the user for clarification or confirmation

## Usage

1. **Install dependencies:**
   ```bash
   pip install -e .
   ```

2. **Set your API key:**
   ```bash
   export OPENROUTER_API_KEY=YOUR_API_KEY
   ```

3. **Run Aurora with your instruction:**
   ```bash
   python -m aurora "Add a function to parse JSON in utils.py"
   ```

## Command-Line Options

- `prompt` (positional): Your natural language instruction.
- `-s`, `--system-prompt`: Custom system prompt.
- `--verbose-http`: Enable HTTP request logging.
- `--verbose-http-raw`: Enable raw HTTP wire-level logging.
- `--verbose-response`: Pretty print the full response.
- `--show-system`: Show model, parameters, and tool definitions, then exit.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Contributing

Pull requests and issues are welcome!
