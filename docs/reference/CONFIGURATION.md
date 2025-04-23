# Configuration

Janito supports robust configuration to tailor its behavior to your needs. Configuration can be managed via environment variables, configuration files, or command-line options.

## Main Options

- **Model Selection**: Choose which LLM backend to use (OpenAI, Azure, etc.).
- **API Keys**: Set your API keys securely via environment variables or config files.
- **Tool Enable/Disable**: Enable or disable specific tools or plugins.
- **Quality Checks**: Configure linting, formatting, and other quality checks.
- **Logging & Output**: Adjust verbosity, output format, and logging destinations.

## How to Configure

1. **Via Environment Variables**: Set variables like `JANITO_API_KEY`, `JANITO_MODEL`, etc.
2. **Via Config File**: Place a `janito.yaml` or `.janitorc` file in your project directory.
3. **Via CLI Options**: Use command-line flags to override config for a session.

---

See the documentation navigation for more details on each option and advanced configuration examples.
