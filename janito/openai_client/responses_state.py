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

from janito.provider_accessors import get_responses_in_server_from_provider


def _init_conversation_state(
    provider: str,
    model: str | None,
    previous_response_id: str | None,
    previous_items: list[dict[str, Any]] | None,
    instructions: str | None,
    prompt: str,
) -> tuple[
    bool,
    str | None,
    list[dict[str, Any]] | None,
    str | list[dict[str, Any]],
    list[dict[str, Any]] | None,
]:
    """Set up the server-side or stateless conversation state.

    Returns ``(responses_in_server, response_id, conversation_items,
    input_items, pending_items)``.  ``pending_items`` only applies to
    server-side conversations: the user messages that are not yet part of a
    completed response in the caller's chain (e.g. an Enter-cancelled prompt
    that must survive the cancel).  The caller keeps them across cancelled
    turns and re-sends them (chained from the last completed response id)
    until a turn completes; ``None`` for stateless conversations.

    The ``responses_in_server`` flag is resolved for the effective ``model``
    (a per-provider/model config override wins over the built-in default).
    """
    responses_in_server = get_responses_in_server_from_provider(provider, model)
    if responses_in_server:
        response_id = previous_response_id
        conversation_items: list[dict[str, Any]] | None = None
        # The first round sends the raw prompt; tool-call rounds send the
        # function_call_output items chained to the previous response.
        input_items: str | list[dict[str, Any]] = prompt
        # Pending user messages (e.g. an Enter-cancelled prompt) that must be
        # re-sent because they are not yet in a completed response the caller
        # chains from.  They are sent as input items chained after the last
        # completed response (previous_response_id), followed by the new
        # prompt; on a cancel they are handed back so the next turn re-sends
        # them (the aborted server response itself is discarded by the
        # provider and cannot be chained from).
        pending_items: list[dict[str, Any]] | None = []
        if previous_items:
            pending_items.extend(dict(item) for item in previous_items)
        pending_items.append(
            {
                "type": "message",
                "role": "user",
                "content": [{"type": "input_text", "text": prompt}],
            }
        )
        if previous_items:
            # Pending messages exist: send them (plus the new prompt) as
            # explicit input items chained from the last completed response.
            input_items = pending_items
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
        pending_items = None
    return (
        responses_in_server,
        response_id,
        conversation_items,
        input_items,
        pending_items,
    )


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
