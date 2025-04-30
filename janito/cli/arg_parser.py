import argparse


def create_parser():
    # Adiciona --list-tools para listar ferramentas registradas
    # (adição incremental segura)

    parser = argparse.ArgumentParser(
        description="OpenRouter API call using OpenAI Python SDK"
    )
    # The positional argument is interpreted as either a prompt or session_id depending on context
    parser.add_argument(
        "input_arg",
        type=str,
        nargs="?",
        help="Prompt to send to the model, or session ID if --continue is used.",
    )

    parser.add_argument(
        "--list",
        nargs="?",
        type=int,
        const=10,
        default=None,
        help="List the last N sessions (default: 10) and exit.",
    )
    parser.add_argument(
        "--view",
        type=str,
        default=None,
        help="View the content of a conversation history by session id and exit.",
    )
    parser.add_argument(
        "--set-provider-config",
        nargs=3,
        metavar=("NAME", "KEY", "VALUE"),
        help="Set a provider config parameter (e.g., --set-provider-config openrouter.ai api_key sk-xxx).",
    )
    parser.add_argument(
        "--lang",
        type=str,
        default=None,
        help="Language for interface messages (e.g., en, pt). Overrides config if set.",
    )

    parser.add_argument(
        "--app-shell",
        action="store_true",
        help="Use the new prompt_toolkit Application-based chat shell (experimental)",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=None,
        help="Maximum tokens for model response (overrides config, default: 200000)",
    )
    parser.add_argument(
        "--max-tools",
        type=int,
        default=None,
        help="Maximum number of tool calls allowed within a chat session (default: unlimited)",
    )
    parser.add_argument(
        "--model",
        "-m",
        type=str,
        default=None,
        help="Model name to use for this session (overrides config, does not persist)",
    )
    parser.add_argument(
        "--max-rounds",
        type=int,
        default=None,
        help="Maximum number of agent rounds per prompt (overrides config, default: 50)",
    )

    # Mutually exclusive group for system prompt options
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "-s",
        "--system",
        type=str,
        default=None,
        help="Optional system prompt as a raw string.",
    )
    group.add_argument(
        "--system-file",
        type=str,
        default=None,
        help="Path to a plain text file to use as the system prompt (no template rendering, takes precedence over --system-prompt)",
    )

    parser.add_argument(
        "-r",
        "--role",
        type=str,
        default=None,
        help="Role description for the default system prompt",
    )
    parser.add_argument(
        "-t",
        "--temperature",
        type=float,
        default=None,
        help="Sampling temperature (e.g., 0.0 - 2.0)",
    )
    parser.add_argument(
        "--verbose-http", action="store_true", help="Enable verbose HTTP logging"
    )
    parser.add_argument(
        "--verbose-http-raw",
        action="store_true",
        help="Enable raw HTTP wire-level logging",
    )
    parser.add_argument(
        "--verbose-response",
        action="store_true",
        help="Pretty print the full response object",
    )
    parser.add_argument(
        "--list-tools",
        action="store_true",
        help="Lista todas as ferramentas registradas e sai.",
    )
    parser.add_argument(
        "--show-system",
        action="store_true",
        help="Show model, parameters, system prompt, and tool definitions, then exit",
    )
    parser.add_argument(
        "--verbose-reason",
        action="store_true",
        help="Print the tool call reason whenever a tool is invoked (for debugging)",
    )
    parser.add_argument(
        "--verbose-tools",
        action="store_true",
        help="Print tool call parameters and results",
    )
    parser.add_argument(
        "-n",
        "--no-tools",
        action="store_true",
        default=False,
        help="Disable tool use (default: enabled)",
    )
    parser.add_argument(
        "--set-local-config",
        type=str,
        default=None,
        help='Set a local config key-value pair, format "key=val"',
    )
    parser.add_argument(
        "--set-global-config",
        type=str,
        default=None,
        help='Set a global config key-value pair, format "key=val"',
    )
    parser.add_argument(
        "--run-config",
        type=str,
        action="append",
        default=None,
        help='Set a runtime (in-memory only) config key-value pair, format "key=val". Can be repeated.',
    )
    parser.add_argument(
        "--show-config",
        action="store_true",
        help="Show effective configuration and exit",
    )
    parser.add_argument(
        "--set-api-key",
        type=str,
        default=None,
        help="Set and save the API key globally",
    )
    parser.add_argument(
        "--version", action="store_true", help="Show program's version number and exit"
    )
    parser.add_argument(
        "--help-config",
        action="store_true",
        help="Show all configuration options and exit",
    )
    parser.add_argument(
        "--continue-session",
        "--continue",
        action="store_true",
        default=False,
        help="Continue from a saved conversation. Uses the session ID from the positional argument if provided, otherwise resumes the most recent session.",
    )
    parser.add_argument(
        "--web", action="store_true", help="Launch the Janito web server instead of CLI"
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Launch the Janito live reload server for web development",
    )
    parser.add_argument(
        "--config-reset-local",
        action="store_true",
        help="Remove the local config file (~/.janito/config.json)",
    )
    parser.add_argument(
        "--config-reset-global",
        action="store_true",
        help="Remove the global config file (~/.janito/config.json)",
    )
    parser.add_argument(
        "--verbose-events",
        action="store_true",
        help="Print all agent events before dispatching to the message handler (for debugging)",
    )
    parser.add_argument(
        "-V",
        "--vanilla",
        action="store_true",
        default=False,
        help="Vanilla mode: disables tools, system prompt, and temperature (unless -t is set)",
    )
    parser.add_argument(
        "-T",
        "--trust-tools",
        action="store_true",
        help="Suppress all tool output (trusted tools mode: only shows output file locations)",
    )
    parser.add_argument(
        "--profile",
        type=str,
        default=None,
        help="Agent Profile name (only 'base' is supported)",
    )
    parser.add_argument(
        "--stream",
        action="store_true",
        help="Enable OpenAI streaming mode (yields tokens as they arrive)",
    )
    parser.add_argument(
        "--verbose-stream",
        action="store_true",
        help="Print raw chunks as they are fetched from OpenAI (for debugging)",
    )
    parser.add_argument(
        "--no-termweb",
        action="store_true",
        help="Disable the built-in lightweight web file viewer for terminal links (enabled by default)",
    )
    parser.add_argument(
        "--termweb-port",
        type=int,
        default=8088,
        help="Port for the termweb server (default: 8088)",
    )
    parser.add_argument(
        "-i",
        "--info",
        action="store_true",
        help="Show basic program info and exit (useful for one-shot shell execution)",
    )
    parser.add_argument(
        "--ntt",
        action="store_true",
        help="Disable tool call reason tracking (no tools tracking)",
    )
    return parser
