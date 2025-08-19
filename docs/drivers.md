# LLM Driver Architecture and Implementation Guide

This document describes the architecture of the LLM driver system in Janito, focusing on the `LLMDriver` base class and the requirements for implementing a new provider-specific driver. It uses the OpenAI driver as a reference example.

## Overview: The `LLMDriver` Base Class

All LLM drivers in Janito inherit from the abstract base class `LLMDriver` (`janito/llm/driver.py`). This class provides a threaded, queue-based interface for interacting with language model APIs in a provider-agnostic way.

### Key Responsibilities

- **Threaded Operation:** Each driver runs a background thread that processes requests from an input queue and emits results/events to an output queue.
- **Standardized Events:** Drivers emit standardized events (e.g., `RequestStarted`, `ResponseReceived`, `RequestFinished`) for downstream consumers.
- **Provider Abstraction:** The base class defines abstract methods for provider-specific logic, ensuring a uniform interface for all drivers.

### Required Abstract Methods

To implement a new driver, you must subclass `LLMDriver` and implement the following methods:

- `def _prepare_api_kwargs(self, config, conversation)`
  - Prepare the keyword arguments for the provider API call, including model name, parameters, and tool schemas if needed.

- `def _call_api(self, driver_input: DriverInput)`
  - Execute the provider API call using the prepared arguments. Should handle cancellation and error reporting.

- `def _convert_completion_message_to_parts(self, message)`
  - Convert the provider's response message into a list of standardized `MessagePart` objects (e.g., text, tool calls).

- `def convert_history_to_api_messages(self, conversation_history)`
  - Convert the internal conversation history to the format required by the provider's API (e.g., a list of dicts for OpenAI).

- `def _get_message_from_result(self, result)`
  - Extract the relevant message object from the provider's API result for further processing.

### Threading and Queues

- Each driver instance has its own `input_queue` and `output_queue`.
- Use the `start()` method to launch the driver's background thread.
- Submit requests by putting `DriverInput` objects into `input_queue`.
- Listen for events/results by reading from `output_queue`.

## Implementing a New Driver: Checklist

1. **Subclass `LLMDriver`.**
2. **Implement all required abstract methods** listed above.
3. **Handle provider-specific configuration** (e.g., API keys, endpoints) in your constructor or via config objects.
4. **Emit standardized events** using the provided event classes (`RequestStarted`, `ResponseReceived`, `RequestFinished`).
5. **Support cancellation** by checking the `cancel_event` in `DriverInput` before and after API calls.
6. **Convert conversation history** to the provider's required format.
7. **Convert provider responses** to standardized message parts for downstream processing.

## Example: OpenAI Driver

See `janito/drivers/openai/driver.py` for a complete example. Highlights:

- Implements all required methods for the OpenAI API.
- Handles tool/function call schemas if tools are present.
- Converts conversation history to OpenAI's message format.
- Extracts usage and other metadata from the API response.
- Handles cancellation and error reporting robustly.

## References

- Base class: `janito/llm/driver.py`
- OpenAI driver: `janito/drivers/openai/driver.py`
- Driver events: `janito/driver_events.py`

