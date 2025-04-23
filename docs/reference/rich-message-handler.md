# Rich Message Handler

The Rich Message Handler is responsible for rendering all output (tool, agent, system) in the terminal using the [rich](https://rich.readthedocs.io/) library for styled and colorized output.

## Features

- **Unified output:** Handles all message types (tool, agent, system) through a single API.
- **Styled messages:** Uses colors and styles for different message types (info, success, error, warning, content, stdout, stderr).
- **Markdown rendering:** Renders assistant/content output as Markdown for improved readability.
- **Trust mode:** Suppresses all output except assistant/content if the `trust` config is enabled.

## Supported Message Types

- `content`: Rendered as Markdown (for assistant/LLM responses)
- `info`: Cyan text
- `success`: Bold green text
- `error`: Bold red text
- `warning`: Bold yellow text
- `progress`: (Custom handler, e.g., progress bars)
- `stdout`: Dark green background
- `stderr`: Dark red background

## Example Usage

```python
handler = RichMessageHandler()
handler.handle_message({"type": "success", "message": "✅ File created"})
handler.handle_message({"type": "content", "message": "**Hello!** This is Markdown."})
```

## Integration

- Used as the default message handler for CLI output in Janito.
- Honors the `trust` config to suppress non-content output for safer automation.
- Extensible: Add new message types or styles as needed.

---

For the overall message handler model, see the [Message Handler Model](message-handler-model.md).
