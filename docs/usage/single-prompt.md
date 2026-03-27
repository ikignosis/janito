# Single Prompt

Run a single prompt and get a response without entering interactive mode.

## Basic Usage

```bash
janito "What is the capital of France?"
```

## With Configuration

```bash
janito --set provider=openai --set model=gpt-4 "Your question here"
```

## Piping Input

You can pipe text into janito:

```bash
echo "Explain this code" | janito
```

```bash
cat readme.md | janito "Summarize this"
```

## Examples

### Quick Question

```bash
janito "What is 2+2?"
```

### With Tools

```bash
janito "List all Python files in the current directory"
```

### With Gmail

```bash
janito --gmail "Show my unread emails from today"
```

### With OneDrive

```bash
janito --onedrive "List my files in Documents"
```

## Exit Codes

Single prompt mode returns standard exit codes:

| Code | Meaning |
|------|---------|
| `0` | Success |
| `1` | Error (configuration, API, etc.) |
| `130` | Interrupted (Ctrl+C) |

## Use Cases

Single prompt mode is ideal for:

- Quick questions
- Scripting and automation
- Integration with other tools
- One-off tasks

For multi-turn conversations, use [interactive mode](interactive-mode.md) instead.
