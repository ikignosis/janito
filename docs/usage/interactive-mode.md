# Interactive Mode

Interactive mode provides a **terminal shell** for multi-turn conversations with context preservation.

> **This is the terminal (CLI/shell) interface.** janito also ships a
> browser-based **web UI** (`janito --web`) with its own chat surface, session
> sidebar, and dashboards. The two share the same engine and tools — see
> [CLI vs Web UI](cli-vs-web.md) and [Web UI](web-ui.md) for the differences.

## Starting Interactive Mode

```bash
janito
```

Without arguments, janito starts an interactive shell:

```
Welcome to janito! Type 'exit' to quit, 'restart' to clear history.
You:
```

## Available Commands

In interactive mode, these commands are available:

| Command | Description |
|---------|-------------|
| `exit` / `quit` | End the session |
| `restart` | Clear conversation history and start fresh |
| `Ctrl+D` / `Ctrl+Z` | Exit (EOF) |
| `Ctrl+C` | Cancel current input (rolls the last prompt/answer back out of the history) |
| `Enter` | While a prompt is pending ("Waiting for response from the API server..."), cancels the request and keeps the prompt in the conversation history |
| `help` | Show available commands |

## Chat Commands

Additional commands available in the terminal shell:

> These commands are implemented by the **terminal shell**. The web chat only
> handles `/tools` on the client (rendered as a card panel); any other slash
> command typed there is sent to the model as ordinary text.

| Command | Description |
|---------|-------------|
| `/help` | Show help information |
| `/skills` | List all available skills (home + local) |
| `/tools` | List all available tools |
| `/plugins` | List the installed plugins (from `<config_dir>/plugins`, default `~/.janito/plugins`), their paths and whether they loaded in the current session |
| `/read <question>` | Send the question to the LLM using the **main** conversation history, but with `tools=` filtered to the read-only (`"r"` permission) tools — the model can read/search/fetch but cannot write or execute. The exchange stays in the main history and rolls back like a normal prompt on cancel |
| `/write <question>` | Send the question to the LLM using the **main** conversation history, but with `tools=` filtered to the write-only (`"w"` permission) tools — the model can create, modify or delete files/dirs but cannot read, search or execute. The exchange stays in the main history and rolls back like a normal prompt on cancel |
| `/show_tools_stats` | Show tool usage statistics (from the SQLite `tools_use.db`) |
| `/changes` | Show the file-changing tool executions recorded for the current prompt |
| `/provider` | Show the current provider and the available providers |
| `/provider <name>` | Switch the session's provider (and model) for this shell session only — the configured default in `config.json` is left unchanged (use `janito --set provider=<name>` to persist a new default; autocompleted). The LLM conversation history is cleared so the new provider/model starts fresh |
| `/model` | Show the current model and the models available from the current provider |
| `/model <name>` | Switch the session's model for this shell session only — the configured default in `config.json` is left unchanged (use `janito --set model=<name>` to persist a new default; autocompleted). Like `--model`, the name is open-ended; when it matches a model available from the current provider its canonical casing is used. The LLM conversation history is cleared so the new model starts fresh |
| `/api_types` | List the API types supported by each built-in provider/model (e.g. `Responses` / `Completions`, plus native-SDK types such as `Anthropic` / `DashScope` / `Gemini`), marking each model's built-in default API type |
| `/thinking` | Show the current session thinking mode status |
| `/thinking on\|off` | Enable or disable runtime config thinking for the current session — the configured default in `config.json` is left unchanged (autocompleted) |
| `/mcp add <name> stdio <cmd>` | Add MCP stdio service |
| `/mcp add <name> http <url>` | Add MCP HTTP service |
| `/mcp list` | List MCP services |
| `/mcp remove <name>` | Remove MCP service |

## Command Autocomplete

As you type a slash command, the shell suggests matching commands in a
dropdown menu. Start typing `/` and every registered command is offered;
narrow the list by typing more characters (for example `/t` suggests
`/tools`). Matching is case-insensitive. Use `Tab` to accept a suggestion, or
the arrow keys to browse the list. Regular chat input (anything not starting
with `/`) is never autocompleted.

Commands that take an argument also autocomplete that argument: after
`/provider `, the provider names are suggested as you type them, e.g.
`/provider op` suggests `openai`. Only providers with an API key stored in
`~/.janito/auth.json` are offered (switching to a key-less provider would
only make the next prompt fail with an authentication error); the full list
is still shown by `/provider` with no argument.

After `/model `, the models available from the **current provider** are
suggested as you type them, e.g. `/model gpt` suggests `gpt-5.6-luna`. The
available set is the provider's built-in models plus any configured
per-model entries in `config.json`; `/model` with no argument lists them
all.

After `/thinking `, `on` and `off` are suggested.

## Examples

### Basic Chat

```bash
$ janito
Welcome to janito! Type 'exit' to quit, 'restart' to clear history.
You: What is Python?
Assistant: Python is a high-level programming language...
You: Tell me more about it
Assistant: Python was created by Guido van Rossum...
You: exit
Goodbye!
```

### Multi-turn with File Operations

```bash
$ janito
You: Read the README.md file and summarize it
Assistant: [File content summary]
You: Now create a similar file called backup.md
Assistant: [File created successfully]
```

### Using Plugins

```bash
$ janito --plugin ../plugins/janito-onedrive-plugin
You: List my files in Documents
Assistant: [Lists OneDrive files]
You: Upload notes.txt to the Documents folder
Assistant: [File uploaded]
```

## Tips

- **Conversation History**: Messages are kept in context during the session
- **Use `restart`**: Clear history if you want a fresh start
- **Exit gracefully**: Use `exit` or `quit` for clean exit

## Tracking Changes (`/changes`)

Every successful tool call whose first argument is a `filepath` and that has
write permission (for example `CreateFile`, `ReplaceTextInFile`, `MoveFile`,
...) is logged to `./.janito/changes.jsonl` while a prompt is being processed.
Read-only tools that also take a `filepath` first argument (such as
`ReadFile`) are not tracked, so the log only ever describes genuine changes.
Only the tool name and its parameters are recorded — never the tool's result.
The file is removed before each new prompt, so it always describes the changes
made while handling the *current* prompt.

Run `/changes` to replay those executions in a friendly, readable format:

- **`CreateFile`** — the written `content` is shown with syntax highlighting
  (the language is guessed from the file path).
- **`ReplaceTextInFile`** — a unified diff between `old_str` and `new_str` is
  generated and shown, syntax-highlighted.
- **Any other tool** — its parameters are shown as pretty-printed JSON.

When no changes have been recorded for the current prompt, `/changes` prints a
friendly message instead.

## Exiting

To exit interactive mode:

```bash
# Method 1: Type exit
You: exit

# Method 2: Type quit
You: quit

# Method 3: Press Ctrl+D (Unix/macOS)

# Method 4: Press Ctrl+Z then Enter (Windows)
```
