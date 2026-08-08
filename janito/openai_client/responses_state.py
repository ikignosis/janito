"""
Conversation-state helpers for the Responses API client.

The Responses API keeps the conversation server-side for most providers
(``responses_in_server`` True) and chains turns with
``previous_response_id``; stateless providers (e.g. DeepSeek) cannot resolve
a previous response id, so the client tracks the full conversation as
Responses input items and re-sends them on every request.  These helpers
build that per-round state and the call parameters; they were extracted from
:mod:`janito.openai_client.conversations_api`.
"""

from typing import Any

from janito.provider_config import get_responses_in_server_from_provider


def _init_conversation_state(
    provider: str,
    previous_response_id: str | None,
    previous_items: list[dict[str, Any]] | None,
    instructions: str | None,
    prompt: str,
) -> tuple[bool, str | None, list[dict[str, Any]] | None, str | list[dict[str, Any]]]:
    """Set up the server-side or stateless conversation state."""
    responses_in_server = get_responses_in_server_from_provider(provider)
    if responses_in_server:
        response_id = previous_response_id
        conversation_items: list[dict[str, Any]] | None = None
        # The first round sends the raw prompt; tool-call rounds send the
        # function_call_output items chained to the previous response.
        input_items: str | list[dict[str, Any]] = prompt
    else:
        # Stateless: never chain with previous_response_id; each request
        # re-sends the entire conversation as input items.
        response_id = None
        conversation_items = list(previous_items or [])
        # Fold the system instructions into the history on the first turn so
        # the stateless server receives the full context on every request.
        if not conversation_items and instructions:
            conversation_items.append(
                {
                    "type": "message",
                    "role": "system",
                    "content": [{"type": "input_text", "text": instructions}],
                }
            )
        conversation_items.append(
            {
                "type": "message",
                "role": "user",
                "content": [{"type": "input_text", "text": prompt}],
            }
        )
        input_items = conversation_items
    return responses_in_server, response_id, conversation_items, input_items


def _build_call_kwargs(
    model: str,
    input_items: str | list[dict[str, Any]],
    max_output_tokens: int | None,
    reasoning_level: str | None,
    preserve_thinking: Any,
    thinking: bool,
    response_id: str | None,
    responses_in_server: bool,
    instructions: str | None,
) -> dict[str, Any]:
    """Build the Responses API call parameters for one round."""
    call_kwargs: dict[str, Any] = {
        "model": model,
        "input": input_items,
        "temperature": 1.0,
    }

    # Add max_output_tokens if max output tokens is set in config
    if max_output_tokens is not None:
        call_kwargs["max_output_tokens"] = max_output_tokens

    # Pass the reasoning level (reasoning_effort) when resolved.
    if reasoning_level:
        call_kwargs["reasoning"] = {"effort": reasoning_level}

    # Pass preserve_thinking in extra_body if defined in config
    if preserve_thinking is not None:
        call_kwargs.setdefault("extra_body", {})[
            "preserve_thinking"
        ] = preserve_thinking

    # Pass enable_thinking in extra_body if thinking flag is set
    if thinking:
        call_kwargs.setdefault("extra_body", {})["enable_thinking"] = True

    # Stream the response. Token usage arrives on the final
    # response.completed event by default (part of the Response object);
    # "usage" is no longer a valid value for include.
    call_kwargs["stream"] = True

    # Chain to the previous server-side response when continuing a
    # server-side conversation (multi-turn or tool-call round). Stateless
    # providers never chain: the full history is already in ``input``.
    if response_id is not None:
        call_kwargs["previous_response_id"] = response_id
    elif responses_in_server and instructions:
        # First turn of a server-side conversation: system instructions
        # are only sent here; the server folds them into the stored
        # conversation.
        call_kwargs["instructions"] = instructions
    return call_kwargs
