# Janito CLI & Configuration Reference

This document lists all command-line flags and configuration options supported by Janito. For most workflows, only a few basic flags are needed (see the README for a quick overview). For advanced usage, refer to the full list below.

---

## CLI Flags

- `input_arg` (positional): Prompt to send to the model, or session ID if --continue is used.
- `--list [N]`: List the last N sessions (default: 10) and exit.
- `--view SESSION_ID`: View the content of a conversation history by session id and exit.
- `--set-provider-config NAME KEY VALUE`: Set a provider config parameter (e.g., --set-provider-config openrouter.ai api_key sk-xxx).
- `--lang LANG`: Language for interface messages (e.g., en, pt). Overrides config if set.
- `--max-tokens N`: Maximum tokens for model response (overrides config, default: 200000).
- `--max-tools N`: Maximum number of tool calls allowed within a chat session (default: unlimited).
- `--model, -m MODEL`: Model name to use for this session (overrides config, does not persist).
- `--max-rounds N`: Maximum number of agent rounds per prompt (overrides config, default: 50).
- `-s, --system PROMPT`: Optional system prompt as a raw string.
- `--system-file FILE`: Path to a plain text file to use as the system prompt (no template rendering, takes precedence over --system).
- `-r, --role ROLE`: Role description for the default system prompt.
- `-t, --temperature FLOAT`: Sampling temperature (e.g., 0.0 - 2.0).
- `--verbose`: Enable general verbose logging.
- `--verbose-http`: Enable verbose HTTP logging.
- `--verbose-http-raw`: Enable raw HTTP wire-level logging.
- `--verbose-response`: Pretty print the full response object.
- `--list-tools`: List all registered tools and exit.
- `--show-system`: Show model, parameters, system prompt, and tool definitions, then exit.
- `--verbose-reason`: Print the tool call reason whenever a tool is invoked (for debugging).
- `--verbose-tools`: Print tool call parameters and results.
- `-n, --no-tools`: Disable tool use (default: enabled).
- `--set-local-config "key=val"`: Set a local config key-value pair.
- `--set-global-config "key=val"`: Set a global config key-value pair.
- `--run-config "key=val"`: Set a runtime (in-memory only) config key-value pair. Can be repeated.
- `--show-config`: Show effective configuration and exit.
- `--set-api-key KEY`: Set and save the API key globally.
- `--version`: Show program's version number and exit.
- `--help-config`: Show all configuration options and exit.
- `--continue-session, --continue [SESSION_ID]`: Continue from a saved conversation. Optionally provide a session ID.
- `--web`: Launch the Janito web server instead of CLI.
- `--live`: Launch the Janito live reload server for web development.
- `--config-reset-local`: Remove the local config file (~/.janito/config.json).
- `--config-reset-global`: Remove the global config file (~/.janito/config.json).
- `--verbose-events`: Print all agent events before dispatching to the message handler (for debugging).
- `-V, --vanilla`: Vanilla mode: disables tools, system prompt, and temperature (unless -t is set).
- `-T, --trust-tools`: Suppress all tool output (trusted tools mode: only shows output file locations).
- `--profile PROFILE`: Agent Profile name (only 'base' is supported).
- `--stream`: Enable OpenAI streaming mode (yields tokens as they arrive).
- `--verbose-stream`: Print raw chunks as they are fetched from OpenAI (for debugging).
- `--no-termweb`: Disable the built-in lightweight web file viewer for terminal links (enabled by default).
- `--termweb-port PORT`: Port for the termweb server (default: 8088).
- `--ntt`: Disable tool call reason tracking (no tools tracking).

---

For additional configuration options, see the comments in your config file or use `--help-config` for a live dump of all available settings.
