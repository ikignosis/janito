# LLM Drivers Architecture

## Overview

The driver layer described below is intended to provide a unified, event-driven interface for interacting with various Large Language Model (LLM) providers (such as OpenAI, Google Gemini, MistralAI, etc.). However, as of this writing, the actual driver code (including the LLMDriver base class and its subclasses) is not present in this directory. The following describes the intended architecture and requirements, but no implementation is currently available here.

## Key Concepts

### Streaming, Event-Driven Interface

- All drivers now use a threaded, queue-based input/output mechanism. The agent sends DriverInput objects to the input queue and reads aggregate DriverEvent objects (notably `ResponseReceived`) from the output queue.
- Drivers emit standardized events (e.g., `ResponseReceived`, `GenerationStarted`, `RequestFinished`, etc.) as the generation progresses. `RequestFinished` covers both success, error, and cancellation cases.
- The new `ResponseReceived` event contains all content, tool calls, and metadata for that turn, so consumers and agents can react more intelligently (especially for automatic tool invocation patterns).

### Threading and Cancellation

- The generation process runs in a background thread, ensuring that the main application/UI remains responsive.
- Cooperative cancellation is supported via a `threading.Event` passed to `stream_generate()`. Consumers can set this event to abort generation early.
- Once cancellation is received (i.e., the event is set), drivers will not execute any new tools or send any new requests to the LLM provider. Ongoing operations will be stopped as soon as possible, ensuring prompt and safe cancellation.

### Consistency and Extensibility

- All drivers inherit from the `LLMDriver` abstract base class and follow the same event and threading conventions.
- Each driver handles provider-specific API calls, tool/function execution, and event emission internally, but always exposes the same external interface.

## Example Usage

```python
import threading
from janito.driver_events import ResponseReceived, RequestFinished

cancel_event = threading.Event()
for event in agent.chat(
    prompt="Tell me a joke.",
    system_prompt="You are a witty assistant.",
    cancel_event=cancel_event
):
    if isinstance(event, ResponseReceived):
        for part in event.content_parts:
            print(part, end="", flush=True)
    elif isinstance(event, RequestFinished) and getattr(event, 'status', None) == 'error':
        print(f"\n[Error: {event.error}]")
```

## Supported Events

- `ResponseReceived`: Aggregate response event containing all content parts, all tool calls, and associated metadata for the turn. The agent now listens for this event by default.
- `GenerationStarted`: Generation process has begun.
- `RequestStarted`, `RequestFinished`: API request lifecycle events. `RequestFinished` includes a `status` field which may be 'success', 'error', or 'cancelled'.
- (Legacy granular events such as `ContentPartFound` are no longer emitted by compliant drivers.)
- (Provider-specific events may also be emitted.)

## Adding a New Driver

To add support for a new LLM provider:

1. Subclass `LLMDriver`.
2. Implement the `_process_driver_input()` method, which consumes a DriverInput object, performs LLM generation, and emits DriverEvent objects to the output queue.
3. Emit standardized events as output is generated.

## Provider-Specific Notes

### Google Gemini (genai) Driver

The Google Gemini driver (and all other modern drivers) now emits a single `ResponseReceived` event per turn, which includes both all content parts and all tool/function calls as parsed from the Gemini API response. Downstream consumers and the agent itself inspect the order and content of these lists to reproduce the true conversational order and context, enabling seamless advanced tool execution. No more per-part events if the driver is up-to-date.

## Design Philosophy

- **Responsiveness:** All generation is non-blocking and can be cancelled at any time.
- **Observability:** Consumers can react to fine-grained events for real-time UIs, logging, or chaining.
- **Simplicity:** A single, modern interface for all drivers.
