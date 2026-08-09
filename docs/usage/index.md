# Usage

Learn different ways to use janito.

## Topics

- [Interactive Mode](interactive-mode.md) - Chat with AI in an interactive terminal shell
- [Single Prompt](single-prompt.md) - Run a single prompt and exit
- [Web UI](web-ui.md) - Browser-based chat with `janito --web`
- [CLI vs Web UI](cli-vs-web.md) - Which features are available in each interface
- [Logging](logging.md) - Enable debug logging and troubleshooting

## Two Interfaces

janito has **two interfaces** that share the same engine, tools, and configuration:

| Interface | How to start | Best for |
|-----------|--------------|----------|
| **Terminal CLI/shell** | `janito "question"`, `janito`, `echo "text" \| janito` | Quick questions, scripting, configuration & secrets, terminal-first workflows |
| **Web UI** | `janito --web` | Browser-based chat with sessions, tool-call cards, dashboards |

Most features (tools, privileges, providers, Gmail/OneDrive, skills, MCP) are
available in **both**; some conveniences exist on only one interface. See
[CLI vs Web UI](cli-vs-web.md) for the full feature-by-feature comparison.

## Input Methods

In the terminal, janito supports multiple ways to provide input:

| Method | Command | Use Case |
|--------|---------|----------|
| Single prompt | `janito "question"` | Quick questions |
| Interactive chat | `janito` | Multi-turn conversations |
| Pipe input | `echo "text" \| janito` | Scripting, integration |

## Next Steps

- Start with [interactive mode](interactive-mode.md) for conversations
- Or learn about [single prompt](single-prompt.md) mode for scripts
- Or launch the [web UI](web-ui.md) for a browser-based chat
- Compare the two interfaces on [CLI vs Web UI](cli-vs-web.md)
