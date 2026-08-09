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
| `/tools` | List all available tools |
| `/show_tools_stats` | Show tool usage statistics (from the SQLite `tools_use.db`) |
| `/changes` | Show the file-changing tool executions recorded for the current prompt |
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

### Using Tools

```bash
$ janito --onedrive
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
