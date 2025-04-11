# Agent Class API

The `Agent` class in `janito.agent.agent` provides the core interface for interacting with language models and tools.

---

## `Agent` Initialization

```
Agent(
    api_key: str,
    model: str = "openrouter/optimus-alpha",
    system_prompt: str | None = None,
    verbose_tools: bool = False,
    tool_handler: ToolHandler | None = None
)
```

### Parameters
- **`api_key`** (`str`): API key for OpenRouter/OpenAI.
- **`model`** (`str`, default: `"openrouter/optimus-alpha"`): Model name.
- **`system_prompt`** (`str | None`, optional): Optional system prompt to guide the assistant.
- **`verbose_tools`** (`bool`, default: `False`): Enable verbose output for tool execution.
- **`tool_handler`** (`ToolHandler | None`, optional): Custom tool handler instance. If not provided, a default `ToolHandler` is created.

---

## `chat()` Method

```
chat(
    messages: list,
    on_content: callable | None = None,
    on_tool_progress: callable | None = None,
    verbose_response: bool = False
) -> dict
```

### Description
Sends a list of messages to the language model and returns the assistant's reply.

### Parameters
- **`messages`** (`list`): Conversation history as a list of message dicts.
- **`on_content`** (`callable | None`, optional): Callback for streaming content tokens.
- **`on_tool_progress`** (`callable | None`, optional): Callback for tool execution progress.
- **`verbose_response`** (`bool`, default: `False`): Include detailed response info if `True`.

### Returns
- **`dict`**: A dictionary containing:
  - `'content'`: The assistant's reply (string).
  - `'usage'`: Token usage stats (dict with `prompt_tokens`, `completion_tokens`, `total_tokens`) or `None`.

---

## Notes
- The `Agent` internally manages conversation state via `ConversationHandler`.
- Tool execution is handled via the `ToolHandler` or a custom handler.
