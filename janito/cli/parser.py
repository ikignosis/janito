"""CLI argument parser for janito."""

import argparse

from .. import __version__


def create_parser() -> argparse.ArgumentParser:
    """Create and configure the CLI argument parser.
    
    Returns:
        argparse.ArgumentParser: Configured argument parser
    """
    parser = argparse.ArgumentParser(
        prog="janito",
        description="OpenAI CLI - Send prompts to OpenAI-compatible endpoints",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Environment Variables:
  OPENAI_BASE_URL    - Base URL of the OpenAI-compatible API endpoint (optional for standard OpenAI)
  OPENAI_API_KEY     - API key for authentication  
  OPENAI_MODEL       - Model name to use for completions

Configuration:
  API keys can be stored in ~/.janito/auth.json using --set-api-key
  If OPENAI_API_KEY is not set, the CLI will try to load from the auth config

Options:
  --set-api-key KEY  Set API key for the specified provider
  --provider NAME    Provider name (e.g., openai, anthropic, azure)
  --model NAME       Model name to use (overrides OPENAI_MODEL env var and config)
  --log LEVELS       Enable logging (e.g., --log=info,debug or --log=warning)
  --list-auth        List configured providers and keys
  --list-tools       List all available built-in tools
  --list-mcp         List all MCP services and their tools
  -Z, --no-system-prompt  Do not set a system prompt or pass any tools to the CLI

Examples:
  janito "What is the capital of France?"                    # Single prompt mode
  echo "Tell me a joke" | janito                             # Pipe input mode
  janito                                                     # Interactive chat mode
  janito --set-api-key sk-xxx --provider openai             # Store OpenAI API key
  janito --set-api-key xxx --provider anthropic             # Store API key for provider
  janito --list-auth                                        # Show configured providers
  janito --list-tools                                       # List available built-in tools
  janito --list-mcp                                         # List MCP services and tools
  janito --info                                             # Show resolved config info
  janito --log=info,debug "Your prompt"                     # Enable logging
  janito --model gpt-4 "Your prompt"                        # Use specific model
  janito --set model=gpt-4                                  # Set config value
  janito --unset model                                      # Remove config value
  janito --get model                                        # Get config value
  janito --set-secret mykey=myvalue                        # Store a secret
  janito --get-secret mykey                                # Retrieve a secret
  janito --list-secrets                                    # List all secrets
  janito --delete-secret mykey                             # Delete a secret
  janito --config                                           # Interactive configuration setup
  janito --provider custom --endpoint https://api.example.com/v1  # Use custom provider
  janito --no-history                                          # Interactive chat without file history
  janito --gmail                                              # Enable Gmail tools and email system prompt
  janito --onedrive                                           # Enable OneDrive tools and file system prompt
  janito --install-skill https://github.com/user/repo/tree/main/skills/git-commit  # Install a skill
  janito --list-skills                                        # List installed skills
  janito --uninstall-skill git-commit                         # Uninstall a skill
        """
    )
    
    parser.add_argument(
        "prompt", 
        nargs="?", 
        help="The prompt to send to the AI (if not provided, starts interactive chat)"
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output (shows model and backend info)"
    )
    
    parser.add_argument(
        "--log",
        metavar="LEVELS",
        help="Enable logging (e.g., --log=info,debug or --log=warning,error)"
    )
    
    parser.add_argument(
        "--info",
        action="store_true",
        help="Print resolved configuration (provider, model, API key) and exit"
    )
    
    parser.add_argument(
        "-Z", "--no-system-prompt",
        action="store_true",
        help="Do not set a system prompt (send user prompt directly)"
    )
    
    parser.add_argument(
        "--list-tools",
        action="store_true",
        help="List all available built-in tools and exit"
    )
    
    parser.add_argument(
        "--list-mcp",
        action="store_true",
        help="List all MCP services and their tools"
    )
    
    parser.add_argument(
        "--set-api-key",
        metavar="KEY",
        help="Set API key for the specified provider (requires --provider)"
    )
    
    parser.add_argument(
        "--model",
        metavar="NAME",
        help="Model name to use for completions (overrides OPENAI_MODEL env var and config)"
    )
    
    parser.add_argument(
        "--provider",
        metavar="NAME",
        help="Provider name (e.g., openai, anthropic, azure, custom)"
    )
    
    parser.add_argument(
        "--endpoint",
        metavar="URL",
        help="API endpoint URL (required for 'custom' provider, or overrides provider base URL)"
    )
    
    parser.add_argument(
        "--list-auth",
        action="store_true",
        help="List configured authentication providers"
    )
    
    parser.add_argument(
        "--set",
        metavar="KEY=VALUE",
        help="Set a config key-value pair in ~/.janito/config.json (e.g., --set model=gpt-4)"
    )
    
    parser.add_argument(
        "--unset",
        metavar="KEY",
        help="Remove a config key from ~/.janito/config.json (e.g., --unset model)"
    )
    
    parser.add_argument(
        "--get",
        metavar="KEY",
        help="Get a config value from ~/.janito/config.json"
    )
    
    parser.add_argument(
        "--set-secret",
        metavar="KEY=VALUE",
        help="Set a secret in ~/.janito/secrets.json (e.g., --set-secret mykey=myvalue)"
    )
    
    parser.add_argument(
        "--get-secret",
        metavar="KEY",
        help="Get a secret value from ~/.janito/secrets.json"
    )
    
    parser.add_argument(
        "--delete-secret",
        metavar="KEY",
        help="Delete a secret from ~/.janito/secrets.json"
    )
    
    parser.add_argument(
        "--list-secrets",
        action="store_true",
        help="List all configured secrets"
    )
    
    parser.add_argument(
        "--config",
        action="store_true",
        help="Interactive configuration setup for provider, API key, and context window"
    )
    
    parser.add_argument(
        "--no-history",
        action="store_true",
        help="Don't persist input history to file (store only in memory)"
    )
    
    parser.add_argument(
        "--gmail",
        action="store_true",
        help="Enable Gmail tools and use email-specific system prompt"
    )
    
    parser.add_argument(
        "--onedrive",
        action="store_true",
        help="Enable OneDrive tools and use file-specific system prompt"
    )
    
    parser.add_argument(
        "--onedrive-auth",
        action="store_true",
        help="Authenticate with Microsoft OneDrive using device code flow"
    )
    
    parser.add_argument(
        "--onedrive-logout",
        action="store_true",
        help="Clear OneDrive authentication tokens"
    )
    
    parser.add_argument(
        "--onedrive-status",
        action="store_true",
        help="Show OneDrive authentication status"
    )
    
    parser.add_argument(
        "--install-skill",
        metavar="URL",
        help="Install a skill from a GitHub URL (e.g., https://github.com/user/awesome-copilot/tree/main/skills/git-commit)"
    )
    
    parser.add_argument(
        "--list-skills",
        action="store_true",
        help="List all installed skills"
    )
    
    parser.add_argument(
        "--uninstall-skill",
        metavar="NAME",
        help="Uninstall a skill by name"
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
        help="Show program's version number and exit"
    )
    
    return parser


def parse_args():
    """Parse command line arguments.
    
    Returns:
        argparse.Namespace: Parsed arguments
    """
    parser = create_parser()
    return parser.parse_args()
