# Configuration & CLI Options

Below are the supported configuration parameters and CLI flags. Some options can be set via config files, CLI flags, or both. Use `janito --help` for a full list, or `janito --help-config` to see all config keys and their descriptions.

| Key / Flag                | Description                                                                                 | How to set                                                      | Default                                    |
|---------------------------|---------------------------------------------------------------------------------------------|-----------------------------------------------------------------|--------------------------------------------|
| `api_key`                 | API key for a compatible language model service                                            | `--set-api-key`, config file                                    | _None_ (required)                          |
| `model`                   | Model name to use for this session                                                          | `--model` (session only), `--set-local-config model=...`, or `--set-global-config` | _(example: gpt-4)_                 |
| `base_url`                | API base URL for your language model service                                                | `--set-local-config base_url=...` or `--set-global-config`      | _(example: https://api.your-model.com)_            |
| `role`                    | Role description for the system prompt                                                      | `--role` or config                                            | "software engineer"                     |
| `system_prompt`           | Override the entire system prompt as a raw string                                           | `--system` or config                                   | _Default prompt_               |
| `system_file`             | Use a plain text file as the system prompt (takes precedence over `system_prompt`)         | `--system-file` (CLI only)                                     | _None_                                     |
| `temperature`             | Sampling temperature (float, e.g., 0.0 - 2.0)                                              | `--temperature` or config                                      | 0.2                                        |
| `max_tokens`              | Maximum tokens for model response                                                          | `--max-tokens` or config                                      | 200000                                     |
| `max_rounds`              | Maximum number of agent rounds per prompt/session                                          | `--max-rounds` or config                                      | 50                                         |
| `max_tools`               | Maximum number of tool calls allowed within a chat session                                 | `--max-tools` or config                                       | _None_ (unlimited)                         |
| `no_tools`           | Disable tool use (no tools passed to agent)                                                | `-n`, `--no-tools` (CLI only)                                   | False                                       |
| `trust`                   | Trust mode: suppresses run_bash_command output, only shows output file locations                  | `--trust` (CLI only)                                           | False                                       |
| `template` / `template.*` | Template context dictionary for prompt rendering (nested or flat keys)                     | Config only                                                    | _None_                                     |

Other config-related CLI flags:

- `--set-local-config key=val`   Set a local config value
- `--set-global-config key=val`  Set a global config value
- `--run-config key=val`         Set a runtime (in-memory only) config value (can be repeated)
- `--show-config`                Show effective configuration and exit
- `--config-reset-local`         Remove the local config file
- `--config-reset-global`        Remove the global config file
- `--set-api-key KEY`            Set and save the API key globally
- `--help-config`                Show all configuration options and exit


### Obtaining an API Key from OpenRouter

To use Janito with OpenRouter, you need an API key:

1. Visit https://openrouter.ai and sign up for an account.
2. After logging in, go to your account dashboard.
3. Navigate to the "API Keys" section.
4. Click "Create new key" and copy the generated API key.
5. Set your API key in Janito using:
   ```bash
   janito --set-api-key YOUR_OPENROUTER_KEY
   ```
   Or add it to your configuration file as `api_key`.

**Keep your API key secure and do not share it publicly.**

### Using Azure OpenAI

For details on using models hosted on Azure OpenAI, see [AZURE_OPENAI.md](./AZURE_OPENAI.md).

Session & shell options:

- `--continue-session`           Continue from the last saved conversation
- `--web`                        Launch the Janito web server instead of CLI

Verbose/debugging flags:

- `--verbose-http`               Enable verbose HTTP logging
- `--verbose-http-raw`           Enable raw HTTP wire-level logging
- `--verbose-response`           Pretty print the full response object
- `--verbose-tools`              Print tool call parameters and results
- `--show-system`                Show model, parameters, system prompt, and tool definitions, then exit
- `--version`                    Show program's version number and exit
