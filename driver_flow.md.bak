# OpenAI Driver Content Flow in Janito

This document explains the updated flow for how content and tool calls are processed in Janito, focusing on the new `ResponseReceived` event and agent logic. This supports both streaming and agent-tool interleaving for advanced use cases.

---

## Flow Overview

1. **Model Response Handling (Driver Layer)**
    - The entrypoint is `OpenAIModelDriver._process_driver_input` (in `janito/drivers/openai/driver.py`).
    - The driver collects output from the model (including content parts, tool call suggestions, etc.), and emits a single `ResponseReceived` event (from `janito/driver_events.py`).
    - This event contains all content, tool calls, normalized timestamps, and relevant metadata.

2. **Agent Decision Loop**
    - The agent (`LLMAgent`, in `janito/llm/agent.py`) processes the `ResponseReceived` event:
        - If the event includes tool calls, the agent invokes those tools using the `tools_adapter`, updates its conversation history with the tool calls and their results, and resubmits to the driver for a new response.
        - If there are no tool calls, the agent yields the `ResponseReceived` event as output (ending the loop for that prompt).
    - This pattern enables fully automated tool-use loops, and naturally supports function-calling workflows (e.g., OpenAI function calling, tool-augmented LLMs).

3. **CLI Core Loop (Chat/Prompt Handler)**
    - In interactive (chat) mode, the CLI (`janito/cli/chat_mode/session.py`, within `ChatSession._chat_loop`) uses the `PromptHandler` to run the user's prompt. The handler now expects `ResponseReceived` events and handles terminal output accordingly.

4. **Event Reporting / Output**
    - The `RichTerminalReporter` (`janito/cli/rich_terminal_reporter.py`) is responsible for displaying content found in the `content_parts` field of `ResponseReceived` events.
    - Only these high-level events are printed as main output, streamlining event handling logic and supporting new LLM APIs.

---

## Sequence Diagram (Updated)

```
User prompt (in CLI)
   ↓
PromptHandler.run_prompt → agent.chat() (yields final ResponseReceived)
   ↓
OpenAI driver produces ResponseReceived (content+tools)
   ↓
LLMAgent detects tool calls → executes via tools_adapter → extends history, repeats until no tool calls
   ↓
ResponseReceived with only content_parts (no tool calls)
   ↓
RichTerminalReporter.on_ResponseReceived prints content
```

---

## Key Classes & Files

- **janito/drivers/openai/driver.py**: Implements the OpenAI driver and emits `ResponseReceived` events only.
- **janito/driver_events.py**: Defines the new `ResponseReceived` (and other) events.
- **janito/llm/agent.py**: Contains smart tool-handling agent event loop.
- **janito/cli/prompt_core.py**: Handles prompt execution and event iteration.
- **janito/cli/rich_terminal_reporter.py**: Handles printing content from `ResponseReceived` to the user.
- **janito/cli/chat_mode/session.py**: Interactive CLI chat session management.

---

## Notes

- This event-driven flow provides both streaming and agent-tool-in-the-loop logic for all drivers. It is compatible with OpenAI and other providers adopting similar response models.
- Tool/function calls from the model are now *only* seen in the aggregated `tool_calls` field of the `ResponseReceived` event.
- Consumers should migrate to listen for `ResponseReceived` events instead of the legacy granular events (`ContentPartFound`, etc.).

---
For more information, see code comments in the affected files or reach out to the maintainers for architectural questions.
